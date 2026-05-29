"""Bible text processing: source loading, mapping, normalization, validation, conversion."""

from __future__ import annotations

from bibliavox.text.jsonl_converter import convert_to_jsonl
from bibliavox.text.mapping import english_to_usx, load_book_mapping
from bibliavox.text.normalizer import normalize_chapter, normalize_text, normalize_verse
from bibliavox.text.source import get_chapter_verses, get_verse_text, load_szit_json
from bibliavox.text.splitter import detect_markers, fix_verses
from bibliavox.text.validator import (
    Discrepancy,
    Severity,
    generate_report,
    validate_book,
    validate_chapter,
)

__all__ = [
    "Discrepancy",
    "Severity",
    "convert_to_jsonl",
    "detect_markers",
    "english_to_usx",
    "fix_verses",
    "generate_report",
    "get_chapter_verses",
    "get_verse_text",
    "load_book_mapping",
    "load_szit_json",
    "normalize_chapter",
    "normalize_text",
    "normalize_verse",
    "validate_book",
    "validate_chapter",
]
