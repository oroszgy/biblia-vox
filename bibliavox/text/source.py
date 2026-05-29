"""SZIT Bible JSON text source loading and verse extraction.

Loads the structured JSON Bible text from peterpolgar/Biblia-json-xml
and provides functions to extract verses by book/chapter/verse.

Data source: H_Kaldi_SZIT.json (Unlicense license)
Structure: {book_name: {chapter: {verse: "text"}}} with English book names
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

# Module-level cache for loaded SZIT data
_SZIT_DATA: dict | None = None

# Repo root: 3 levels up from bibliavox/text/source.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_RAW_DIR = _REPO_ROOT / "data" / "raw" / "text"


def load_szit_json(data_dir: Path | None = None) -> dict:
    """Load the SZIT Bible JSON from disk.

    Args:
        data_dir: Path to directory containing H_Kaldi_SZIT.json.
                  Defaults to data/raw/text/ relative to repo root.

    Returns:
        Parsed JSON dict with English book names as keys.

    Raises:
        FileNotFoundError: If H_Kaldi_SZIT.json is not found.
        json.JSONDecodeError: If the file is malformed JSON.
    """
    global _SZIT_DATA
    if _SZIT_DATA is not None:
        return _SZIT_DATA

    if data_dir is None:
        data_dir = _DEFAULT_RAW_DIR

    json_path = Path(data_dir) / "H_Kaldi_SZIT.json"
    with open(json_path, encoding="utf-8") as f:
        content = f.read()

    # SZIT file uses Python literal format (single quotes), not standard JSON
    try:
        _SZIT_DATA = ast.literal_eval(content)
    except (ValueError, SyntaxError):
        # Fallback to standard JSON if literal_eval fails
        _SZIT_DATA = json.loads(content)

    return _SZIT_DATA


def get_chapter_verses(
    book_name: str,
    chapter: int,
    data: dict | None = None,
) -> dict[int, str]:
    """Get all verses for a specific book and chapter.

    Args:
        book_name: English book name (e.g., "Genesis").
        chapter: 1-based chapter number.
        data: Optional pre-loaded SZIT data dict. Loads from disk if None.

    Returns:
        Dict of {verse_num: verse_text} with integer keys.

    Raises:
        KeyError: If book or chapter not found.
    """
    if data is None:
        data = load_szit_json()

    if book_name not in data:
        raise KeyError(f"Book not found: {book_name}")

    book_data = data[book_name]
    chapter_key = str(chapter)

    if chapter_key not in book_data:
        raise KeyError(f"Chapter {chapter} not found in {book_name}")

    return {int(k): v for k, v in book_data[chapter_key].items()}


def get_verse_text(
    book_name: str,
    chapter: int,
    verse: int,
    data: dict | None = None,
) -> str:
    """Get text of a specific verse.

    Args:
        book_name: English book name (e.g., "Genesis").
        chapter: 1-based chapter number.
        verse: 1-based verse number.
        data: Optional pre-loaded SZIT data dict. Loads from disk if None.

    Returns:
        Verse text as string.

    Raises:
        KeyError: If book, chapter, or verse not found.
    """
    if data is None:
        data = load_szit_json()

    if book_name not in data:
        raise KeyError(f"Book not found: {book_name}")

    book_data = data[book_name]
    chapter_key = str(chapter)

    if chapter_key not in book_data:
        raise KeyError(f"Chapter {chapter} not found in {book_name}")

    verse_key = str(verse)
    if verse_key not in book_data[chapter_key]:
        raise KeyError(f"Verse {verse} not found in {book_name} {chapter}")

    return book_data[chapter_key][verse_key]
