"""Versification schema for the 73-book Catholic Bible.

Provides chapter counts and verse counts per chapter for every book.
Data is loaded from static JSON (no runtime network dependency).

Data source: szentiras.eu tdverse schema (AGPL licensed).
Static JSON at data/reference/versification.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Module-level cache
_SCHEMAS: list[BookSchema] | None = None

# Repo root: 3 levels up from bibliavox/reference/schema.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data" / "reference"


@dataclass(frozen=True, slots=True)
class BookSchema:
    """Versification schema for a single Bible book."""

    usx_code: str
    """Paratext USX code (e.g., 'GEN')."""

    chapter_count: int
    """Total number of chapters in the book."""

    chapters: dict[int, int]
    """Mapping of chapter number to verse count (e.g., {1: 31, 2: 25, ...})."""


def load_versification(data_dir: Path | None = None) -> list[BookSchema]:
    """Load versification data from the static JSON reference.

    Args:
        data_dir: Path to directory containing versification.json.
                  Defaults to data/reference/ relative to repo root.

    Returns:
        List of BookSchema instances.

    Raises:
        FileNotFoundError: If versification.json is not found.
        json.JSONDecodeError: If versification.json is malformed.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    versification_path = Path(data_dir) / "versification.json"
    with open(versification_path, encoding="utf-8") as f:
        raw = json.load(f)

    schemas = []
    for item in raw:
        # JSON keys are strings; convert to int
        chapters = {int(k): v for k, v in item["chapters"].items()}
        schemas.append(
            BookSchema(
                usx_code=item["usx_code"],
                chapter_count=item["chapter_count"],
                chapters=chapters,
            )
        )
    return schemas


def _get_schemas_cache() -> list[BookSchema]:
    """Get or initialize the module-level schemas cache."""
    global _SCHEMAS
    if _SCHEMAS is None:
        _SCHEMAS = load_versification()
    return _SCHEMAS


def get_versification(
    usx_code: str,
    schemas: list[BookSchema] | None = None,
) -> BookSchema | None:
    """Get the full versification schema for a book.

    Args:
        usx_code: Paratext USX code (e.g., 'GEN').
        schemas: Optional list of schemas. Uses cache if None.

    Returns:
        BookSchema if found, None otherwise.
    """
    if schemas is None:
        schemas = _get_schemas_cache()

    usx_upper = usx_code.upper()
    for schema in schemas:
        if schema.usx_code == usx_upper:
            return schema
    return None


def get_chapter_count(
    usx_code: str,
    schemas: list[BookSchema] | None = None,
) -> int:
    """Get the number of chapters in a book.

    Args:
        usx_code: Paratext USX code (e.g., 'GEN').
        schemas: Optional list of schemas. Uses cache if None.

    Returns:
        Number of chapters.

    Raises:
        KeyError: If the book is not found.
    """
    if schemas is None:
        schemas = _get_schemas_cache()

    schema = get_versification(usx_code, schemas)
    if schema is None:
        raise KeyError(f"Book not found: {usx_code}")
    return schema.chapter_count


def get_verse_count(
    usx_code: str,
    chapter: int,
    schemas: list[BookSchema] | None = None,
) -> int:
    """Get the number of verses in a specific chapter.

    Args:
        usx_code: Paratext USX code (e.g., 'GEN').
        chapter: Chapter number (1-based).
        schemas: Optional list of schemas. Uses cache if None.

    Returns:
        Number of verses in the chapter.

    Raises:
        KeyError: If the book or chapter is not found.
    """
    if schemas is None:
        schemas = _get_schemas_cache()

    schema = get_versification(usx_code, schemas)
    if schema is None:
        raise KeyError(f"Book not found: {usx_code}")
    if chapter not in schema.chapters:
        raise KeyError(f"Chapter {chapter} not found in {usx_code}")
    return schema.chapters[chapter]
