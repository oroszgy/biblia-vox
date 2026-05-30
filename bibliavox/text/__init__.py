"""Bible text processing: source loading, mapping, normalization, validation, conversion."""

from __future__ import annotations

from bibliavox.text.jsonl_converter import convert_to_jsonl
from bibliavox.text.mapping import english_to_usx, load_book_mapping
from bibliavox.text.cross_validator import cross_validate_corpora
from bibliavox.text.mek_source import (
    build_mek_corpus,
    download_mek_book,
    parse_and_cache_mek_chapters,
)
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
    "build_mek_corpus",
    "convert_to_jsonl",
    "cross_validate_corpora",
    "detect_markers",
    "download_mek_book",
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
    "parse_and_cache_mek_chapters",
    "validate_book",
    "validate_chapter",
]
