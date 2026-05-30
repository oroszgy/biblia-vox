"""Audio preparation orchestration for chapter artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from bibliavox.audio.convert import convert_to_wav
from bibliavox.audio.metadata import probe_audio
from bibliavox.audio.seek_index import build_seek_index


class PrepareChapterResult(TypedDict):
    """Result payload for chapter preparation orchestration."""

    status: str
    wav_path: Path
    meta_path: Path
    index_path: Path


def _now_iso_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _is_valid_existing_artifacts(
    *,
    meta_path: Path,
    index_path: Path,
    wav_path: Path,
    expected_book: str,
    expected_chapter: int,
) -> bool:
    try:
        meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False

    if not isinstance(meta_payload, dict) or not isinstance(index_payload, dict):
        return False

    meta_book = str(meta_payload.get("book_usx", "")).upper()
    meta_chapter = int(meta_payload.get("chapter", -1))
    if meta_book != expected_book or meta_chapter != expected_chapter:
        return False

    wav_from_meta = Path(str(meta_payload.get("wav_path", "")))
    wav_from_index = Path(str(index_payload.get("wav_path", "")))
    resolved_wav = wav_path.resolve()
    return (
        wav_from_meta.resolve() == resolved_wav
        and wav_from_index.resolve() == resolved_wav
    )


def prepare_chapter(
    book_usx: str,
    chapter: int,
    *,
    raw_root: Path = Path("data/raw/audio"),
    prepared_root: Path = Path("data/prepared/audio"),
    force: bool = False,
) -> PrepareChapterResult:
    """Prepare chapter artifacts by running convert -> metadata -> seek-index."""
    normalized_book = book_usx.upper()
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    input_mp3 = raw_root / normalized_book / f"{chapter:03d}.mp3"
    chapter_root = prepared_root / normalized_book
    wav_path = chapter_root / f"{chapter:03d}.wav"
    meta_path = chapter_root / f"{chapter:03d}.meta.json"
    index_path = chapter_root / f"{chapter:03d}.index.json"

    if not input_mp3.exists():
        raise FileNotFoundError(f"Input MP3 not found: {input_mp3}")

    if wav_path.exists() and meta_path.exists() and index_path.exists() and not force:
        if _is_valid_existing_artifacts(
            meta_path=meta_path,
            index_path=index_path,
            wav_path=wav_path,
            expected_book=normalized_book,
            expected_chapter=chapter,
        ):
            return PrepareChapterResult(
                status="skipped",
                wav_path=wav_path,
                meta_path=meta_path,
                index_path=index_path,
            )

    converted_wav = convert_to_wav(input_mp3, wav_path, force=force)
    metadata = probe_audio(converted_wav)

    meta_payload = {
        **metadata,
        "wav_path": str(converted_wav),
        "book_usx": normalized_book,
        "chapter": chapter,
        "created_at": _now_iso_utc(),
    }
    chapter_root.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps(meta_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    written_index = build_seek_index(
        converted_wav,
        book_usx=normalized_book,
        chapter=chapter,
    )

    return PrepareChapterResult(
        status="prepared",
        wav_path=converted_wav,
        meta_path=meta_path,
        index_path=written_index,
    )
