"""Verse count validation and JSON discrepancy reporting.

Validates verse counts against the versification schema and generates
structured JSON reports for any mismatches found.

Severity levels:
- ERROR: Missing book/chapter in schema
- WARNING: Verse count mismatch, empty verse text
- INFO: Extra data not in schema
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum

from bibliavox.reference.schema import (
    BookSchema,
    get_versification,
    load_versification,
)


class Severity(Enum):
    """Discrepancy severity levels."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True, slots=True)
class Discrepancy:
    """A single validation discrepancy."""

    book: str  # USX code
    chapter: int
    verse: int | None  # None for chapter-level issues
    severity: Severity
    details: str


def validate_chapter(
    usx_code: str,
    chapter: int,
    verses: dict[int, str],
    schemas: list[BookSchema] | None = None,
) -> list[Discrepancy]:
    """Validate a chapter's verses against versification schema.

    Checks:
    - Verse count matches schema
    - No empty verse text
    - No duplicate verse numbers (implicit in dict)
    - Chapter exists in schema

    Args:
        usx_code: USX code of the book (e.g., "GEN").
        chapter: 1-based chapter number.
        verses: Dict of {verse_num: verse_text}.
        schemas: Optional list of BookSchema. Loads from reference data if None.

    Returns:
        List of Discrepancy instances found.
    """
    discrepancies: list[Discrepancy] = []

    if schemas is None:
        schemas = load_versification()

    schema = get_versification(usx_code, schemas)
    if schema is None:
        discrepancies.append(
            Discrepancy(
                book=usx_code,
                chapter=chapter,
                verse=None,
                severity=Severity.ERROR,
                details=f"Book {usx_code} not found in versification schema",
            )
        )
        return discrepancies

    if chapter not in schema.chapters:
        discrepancies.append(
            Discrepancy(
                book=usx_code,
                chapter=chapter,
                verse=None,
                severity=Severity.ERROR,
                details=f"Chapter {chapter} not found in {usx_code} versification schema",
            )
        )
        return discrepancies

    expected_count = schema.chapters[chapter]
    actual_count = len(verses)

    if actual_count != expected_count:
        discrepancies.append(
            Discrepancy(
                book=usx_code,
                chapter=chapter,
                verse=None,
                severity=Severity.WARNING,
                details=f"Verse count mismatch: expected {expected_count}, got {actual_count}",
            )
        )

    # Check for empty verses
    for verse_num, text in verses.items():
        if not text or not text.strip():
            discrepancies.append(
                Discrepancy(
                    book=usx_code,
                    chapter=chapter,
                    verse=verse_num,
                    severity=Severity.WARNING,
                    details=f"Empty verse text at {usx_code} {chapter}:{verse_num}",
                )
            )

    return discrepancies


def validate_book(
    usx_code: str,
    book_data: dict,
    mapping: dict[str, str],
    schemas: list[BookSchema] | None = None,
) -> list[Discrepancy]:
    """Validate all chapters in a book.

    Args:
        usx_code: USX code of the book.
        book_data: Book data from SZIT JSON (chapter → verse → text).
        mapping: English name → USX code mapping.
        schemas: Optional list of BookSchema.

    Returns:
        List of all Discrepancy instances found.
    """
    # Find English name for this USX code
    english_name = None
    for eng, usx in mapping.items():
        if usx == usx_code:
            english_name = eng
            break

    if english_name is None or english_name not in book_data:
        return [
            Discrepancy(
                book=usx_code,
                chapter=0,
                verse=None,
                severity=Severity.ERROR,
                details=f"Book {usx_code} ({english_name}) not found in SZIT JSON",
            )
        ]

    all_discrepancies: list[Discrepancy] = []
    for chapter_str, verses_data in book_data[english_name].items():
        chapter = int(chapter_str)
        verses = {int(k): v for k, v in verses_data.items()}
        all_discrepancies.extend(validate_chapter(usx_code, chapter, verses, schemas))

    return all_discrepancies


def generate_report(discrepancies: list[Discrepancy]) -> str:
    """Generate JSON discrepancy report.

    Args:
        discrepancies: List of Discrepancy instances to report.

    Returns:
        JSON string with structured discrepancy records.
    """
    return json.dumps(
        [
            {
                "book": d.book,
                "chapter": d.chapter,
                "verse": d.verse,
                "severity": d.severity.value,
                "details": d.details,
            }
            for d in discrepancies
        ],
        indent=2,
        ensure_ascii=False,
    )
