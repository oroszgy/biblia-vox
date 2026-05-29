"""Audio playlist discovery and inventory diagnostics."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TypedDict

from bibliavox.reference.books import get_all_books
from bibliavox.reference.schema import load_versification

BASE_AUDIO_URL = "https://mek.oszk.hu/08800/08820/mp3"


class ParsedPlaylistItem(TypedDict):
    """Parsed M3U track metadata."""

    relative_path: str
    extinf_sec: int | None


class ManifestItem(TypedDict):
    """Canonical chapter audio manifest record."""

    book_usx: str
    chapter: int
    url: str
    relative_path: str
    extinf_sec: int | None
    source: str


def _normalize_relative_mp3_path(raw_path: str) -> str | None:
    normalized = raw_path.strip().replace("\\", "/")
    if not normalized:
        return None

    lowered = normalized.lower()
    if not lowered.endswith(".mp3"):
        return None

    candidate = PurePosixPath(normalized)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None

    return str(candidate)


def parse_m3u(lines: list[str]) -> list[ParsedPlaylistItem]:
    """Parse M3U lines into normalized MP3 entries with EXTINF seconds."""
    parsed: list[ParsedPlaylistItem] = []
    pending_extinf: int | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if line.startswith("#EXTINF:"):
            raw_seconds = line.split(":", 1)[1].split(",", 1)[0]
            try:
                pending_extinf = int(raw_seconds)
            except ValueError:
                pending_extinf = None
            continue

        normalized_path = _normalize_relative_mp3_path(line)
        if normalized_path is None:
            continue

        parsed.append(
            ParsedPlaylistItem(
                relative_path=normalized_path,
                extinf_sec=pending_extinf,
            )
        )
        pending_extinf = None

    return parsed


def _extract_book_and_chapter(relative_path: str) -> tuple[int, int] | None:
    path = PurePosixPath(relative_path)
    parts = path.parts
    if len(parts) < 3:
        return None

    book_dir = parts[-2]
    book_match = re.match(r"^(\d+)_", book_dir)
    if book_match is None:
        return None

    chapter_match = re.search(r"-(\d+)\.mp3$", path.name, flags=re.IGNORECASE)
    if chapter_match is None:
        return None

    return int(book_match.group(1)), int(chapter_match.group(1))


def build_audio_manifest(
    parsed_entries: list[ParsedPlaylistItem],
) -> list[ManifestItem]:
    """Map parsed playlist entries into canonical manifest records."""
    books = get_all_books()
    manifest: list[ManifestItem] = []

    for entry in parsed_entries:
        extracted = _extract_book_and_chapter(entry["relative_path"])
        if extracted is None:
            continue

        book_index, chapter = extracted
        if book_index < 1 or book_index > len(books):
            continue

        book = books[book_index - 1]
        manifest.append(
            ManifestItem(
                book_usx=book.usx_code,
                chapter=chapter,
                url=f"{BASE_AUDIO_URL}/{entry['relative_path']}",
                relative_path=entry["relative_path"],
                extinf_sec=entry["extinf_sec"],
                source="mek.m3u",
            )
        )

    return manifest


def inventory_report(manifest: list[ManifestItem]) -> dict[str, dict[str, list[int]]]:
    """Compare manifest chapter inventory against versification schema."""
    by_book: dict[str, set[int]] = {}
    for item in manifest:
        by_book.setdefault(item["book_usx"], set()).add(item["chapter"])

    missing_vs_schema: dict[str, list[int]] = {}
    extra_vs_schema: dict[str, list[int]] = {}

    for schema in load_versification():
        expected = set(range(1, schema.chapter_count + 1))
        available = by_book.get(schema.usx_code, set())

        missing = sorted(expected - available)
        if missing:
            missing_vs_schema[schema.usx_code] = missing

        extra = sorted(available - expected)
        if extra:
            extra_vs_schema[schema.usx_code] = extra

    return {
        "missing_vs_schema": missing_vs_schema,
        "extra_vs_schema": extra_vs_schema,
    }
