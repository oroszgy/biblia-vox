"""Dataset coverage audit for text and audio artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import httpx

from bibliavox.audio.discovery import (
    BASE_AUDIO_URL,
    ManifestItem,
    build_audio_manifest,
    inventory_report,
    parse_m3u,
)
from bibliavox.reference.books import Book, get_all_books
from bibliavox.reference.schema import BookSchema, load_versification


@dataclass(frozen=True, slots=True)
class KnownGaps:
    """Known tolerated gaps loaded from JSON policy."""

    text: dict[str, set[int]]
    audio: dict[str, set[int]]
    audio_extra: dict[str, set[int]]


def _normalize_gap_map(raw: dict[str, object] | None) -> dict[str, set[int]]:
    if raw is None:
        return {}

    normalized: dict[str, set[int]] = {}
    for usx, chapters in raw.items():
        if not isinstance(usx, str) or not isinstance(chapters, list):
            continue
        normalized[usx.upper()] = {
            int(chapter)
            for chapter in chapters
            if isinstance(chapter, int)
            or (isinstance(chapter, str) and chapter.isdigit())
        }
    return normalized


def load_known_gaps(path: Path) -> KnownGaps:
    """Load known source gaps policy file.

    Missing file is treated as empty policy.
    """
    if not path.exists():
        return KnownGaps(text={}, audio={}, audio_extra={})

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        return KnownGaps(text={}, audio={}, audio_extra={})

    return KnownGaps(
        text=_normalize_gap_map(payload.get("text")),
        audio=_normalize_gap_map(payload.get("audio")),
        audio_extra=_normalize_gap_map(payload.get("audio_extra")),
    )


def _missing_local_audio(
    usx: str,
    expected: set[int],
    raw_root: Path,
    prepared_root: Path,
) -> dict[str, list[int]]:
    raw: list[int] = []
    wav: list[int] = []
    index: list[int] = []
    meta: list[int] = []

    for chapter in sorted(expected):
        stem = f"{chapter:03d}"
        if not (raw_root / usx / f"{stem}.mp3").exists():
            raw.append(chapter)
        if not (prepared_root / usx / f"{stem}.wav").exists():
            wav.append(chapter)
        if not (prepared_root / usx / f"{stem}.index.json").exists():
            index.append(chapter)
        if not (prepared_root / usx / f"{stem}.meta.json").exists():
            meta.append(chapter)

    return {
        "raw": raw,
        "wav": wav,
        "index": index,
        "meta": meta,
    }


def _classify_book_gaps(
    text_missing: list[int],
    remote_audio_missing: list[int],
    local_audio: dict[str, list[int]],
) -> str:
    remote_set = set(remote_audio_missing)
    raw_set = set(local_audio["raw"])
    wav_set = set(local_audio["wav"])
    idx_set = set(local_audio["index"])
    meta_set = set(local_audio["meta"])

    if raw_set and remote_set and raw_set.issubset(remote_set):
        return "upstream_source_gap"
    if raw_set and not remote_set:
        return "local_download_gap"
    if (wav_set or idx_set or meta_set) and not raw_set:
        return "prepare_pipeline_gap"
    if text_missing and not raw_set and not wav_set and not idx_set and not meta_set:
        return "text_source_or_mapping_gap"
    if text_missing or raw_set or wav_set or idx_set or meta_set:
        return "mixed_or_unknown_gap"
    return "none"


def _load_mek_text_coverage(mek_jsonl_path: Path) -> dict[str, set[int]]:
    """Load MEK JSONL and return mapping of USX code to set of chapter numbers."""
    coverage: dict[str, set[int]] = {}
    if not mek_jsonl_path.exists():
        return coverage
    with open(mek_jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            book = verse.get("book", "")
            chapter = verse.get("chapter")
            if book and chapter is not None:
                if book not in coverage:
                    coverage[book] = set()
                coverage[book].add(int(chapter))
    return coverage


def _fetch_remote_manifest() -> list[ManifestItem]:
    playlist_url = f"{BASE_AUDIO_URL}/biblia.m3u"
    timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=10.0)
    response = httpx.get(playlist_url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return build_audio_manifest(parse_m3u(response.text.splitlines()))


def audit_coverage(
    *,
    allow_deuterocanonical_missing: bool = False,
    allow_known_source_gaps: bool = False,
    fail_on_unclassified: bool = False,
    known_gaps_path: Path = Path("data/reference/known_gaps.json"),
    raw_audio_root: Path = Path("data/raw/audio"),
    prepared_audio_root: Path = Path("data/prepared/audio"),
    mek_jsonl_path: Path = Path("data/processed/text/mek.jsonl"),
    include_remote_audio: bool = True,
    schemas: list[BookSchema] | None = None,
    books: list[Book] | None = None,
    remote_manifest: list[ManifestItem] | None = None,
) -> dict[str, object]:
    """Run strict coverage audit and return structured report."""
    schemas = schemas or load_versification()
    books = books or get_all_books()
    mek_coverage = _load_mek_text_coverage(mek_jsonl_path)
    known = load_known_gaps(known_gaps_path)

    by_book = {book.usx_code: book for book in books}
    scoped_schemas = [
        schema
        for schema in schemas
        if not (
            allow_deuterocanonical_missing and by_book[schema.usx_code].deuterocanonical
        )
    ]
    scoped_usx_codes = {schema.usx_code for schema in scoped_schemas}

    remote_missing: dict[str, list[int]] = {}
    remote_extra: dict[str, list[int]] = {}
    remote_error: str | None = None
    if include_remote_audio:
        try:
            manifest = (
                remote_manifest
                if remote_manifest is not None
                else _fetch_remote_manifest()
            )
            inventory = inventory_report(manifest)
            remote_missing = inventory["missing_vs_schema"]
            remote_extra = inventory["extra_vs_schema"]
        except Exception as exc:  # noqa: BLE001
            remote_error = str(exc)

    text_missing: dict[str, list[int]] = {}
    text_extra: dict[str, list[int]] = {}
    audio_raw_missing: dict[str, list[int]] = {}
    audio_wav_missing: dict[str, list[int]] = {}
    audio_index_missing: dict[str, list[int]] = {}
    audio_meta_missing: dict[str, list[int]] = {}
    classification: dict[str, dict[str, object]] = {}

    for schema in scoped_schemas:
        usx = schema.usx_code
        expected = set(range(1, schema.chapter_count + 1))

        actual_text_chapters = mek_coverage.get(usx, set())

        missing_text_chapters = sorted(expected - actual_text_chapters)
        extra_text_chapters = sorted(actual_text_chapters - expected)
        if missing_text_chapters:
            text_missing[usx] = missing_text_chapters
        if extra_text_chapters:
            text_extra[usx] = extra_text_chapters

        local_audio = _missing_local_audio(
            usx, expected, raw_audio_root, prepared_audio_root
        )
        if local_audio["raw"]:
            audio_raw_missing[usx] = local_audio["raw"]
        if local_audio["wav"]:
            audio_wav_missing[usx] = local_audio["wav"]
        if local_audio["index"]:
            audio_index_missing[usx] = local_audio["index"]
        if local_audio["meta"]:
            audio_meta_missing[usx] = local_audio["meta"]

        remote_for_book = remote_missing.get(usx, [])
        classification[usx] = {
            "text_missing": missing_text_chapters,
            "remote_audio_missing": remote_for_book,
            "local_raw_missing": local_audio["raw"],
            "local_wav_missing": local_audio["wav"],
            "local_index_missing": local_audio["index"],
            "local_meta_missing": local_audio["meta"],
            "likely_cause": _classify_book_gaps(
                missing_text_chapters,
                remote_for_book,
                local_audio,
            ),
        }

    unresolved = {
        "text_missing": 0,
        "audio_raw_missing": 0,
        "audio_wav_missing": 0,
        "audio_index_missing": 0,
        "audio_meta_missing": 0,
    }
    for usx, chapters in text_missing.items():
        for chapter in chapters:
            if allow_known_source_gaps and chapter in known.text.get(usx, set()):
                continue
            unresolved["text_missing"] += 1

    for artifact_name, gaps in (
        ("audio_raw_missing", audio_raw_missing),
        ("audio_wav_missing", audio_wav_missing),
        ("audio_index_missing", audio_index_missing),
        ("audio_meta_missing", audio_meta_missing),
    ):
        for usx, chapters in gaps.items():
            for chapter in chapters:
                if allow_known_source_gaps and chapter in known.audio.get(usx, set()):
                    continue
                unresolved[artifact_name] += 1

    unresolved_books = {
        usx
        for usx, payload in classification.items()
        if (
            payload["text_missing"]
            or payload["local_raw_missing"]
            or payload["local_wav_missing"]
            or payload["local_index_missing"]
            or payload["local_meta_missing"]
        )
    }
    unresolved_unclassified = sum(
        1
        for usx in unresolved_books
        if classification[usx]["likely_cause"] in {"mixed_or_unknown_gap"}
    )

    complete = all(value == 0 for value in unresolved.values())
    if fail_on_unclassified and unresolved_unclassified > 0:
        complete = False

    return {
        "options": {
            "allow_deuterocanonical_missing": allow_deuterocanonical_missing,
            "allow_known_source_gaps": allow_known_source_gaps,
            "fail_on_unclassified": fail_on_unclassified,
            "include_remote_audio": include_remote_audio,
            "known_gaps_path": str(known_gaps_path),
        },
        "summary": {
            "books_scoped": len(scoped_schemas),
            "text_missing_total": sum(len(v) for v in text_missing.values()),
            "text_extra_total": sum(len(v) for v in text_extra.values()),
            "audio_raw_missing_total": sum(len(v) for v in audio_raw_missing.values()),
            "audio_wav_missing_total": sum(len(v) for v in audio_wav_missing.values()),
            "audio_index_missing_total": sum(
                len(v) for v in audio_index_missing.values()
            ),
            "audio_meta_missing_total": sum(
                len(v) for v in audio_meta_missing.values()
            ),
            "unresolved": unresolved,
            "unresolved_unclassified_books": unresolved_unclassified,
        },
        "gaps": {
            "text_missing": text_missing,
            "text_extra": text_extra,
            "audio_raw_missing": audio_raw_missing,
            "audio_wav_missing": audio_wav_missing,
            "audio_index_missing": audio_index_missing,
            "audio_meta_missing": audio_meta_missing,
            "remote_audio_missing": {
                usx: chapters
                for usx, chapters in remote_missing.items()
                if usx in scoped_usx_codes
            },
            "remote_audio_extra": {
                usx: chapters
                for usx, chapters in remote_extra.items()
                if usx in scoped_usx_codes
            },
        },
        "remote_audio_error": remote_error,
        "classification": classification,
        "complete": complete,
    }
