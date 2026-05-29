"""Bible book catalog for the 73-book Catholic canon.

Provides the Szent István Társulat (SZIT) Hungarian translation book data:
- Hungarian names, abbreviations
- USX codes (Paratext standard)
- Book numbers (gepi encoding base)
- Testament and deuterocanonical classification

Data source: szentiras.eu tdverse schema (AGPL licensed).
Static JSON at data/reference/books.json (no runtime network dependency).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Module-level cache for loaded books
_BOOKS: list[Book] | None = None

# Repo root: 3 levels up from bibliavox/reference/books.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data" / "reference"


@dataclass(frozen=True, slots=True)
class Book:
    """A book of the Catholic Bible."""

    usx_code: str
    """Paratext USX code (e.g., 'GEN', 'MRK', 'BAR')."""

    hungarian_name: str
    """Hungarian name in SZIT translation (e.g., 'Teremtés', 'Márk evangéliuma')."""

    abbreviation: str
    """Standard Hungarian abbreviation (e.g., 'Ter', 'Mk', 'Bölcs')."""

    book_number: int
    """Gepi encoding base number (e.g., 101 for GEN, 401 for MAT)."""

    testament: str
    """'OT' for Old Testament, 'NT' for New Testament."""

    deuterocanonical: bool
    """True for deuterocanonical (apokrif) books."""


def load_books(data_dir: Path | None = None) -> list[Book]:
    """Load all Bible books from the static JSON reference data.

    Args:
        data_dir: Path to the directory containing books.json.
                  Defaults to data/reference/ relative to repo root.

    Returns:
        List of Book instances in canonical order.

    Raises:
        FileNotFoundError: If books.json is not found.
        json.JSONDecodeError: If books.json is malformed.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    books_path = Path(data_dir) / "books.json"
    with open(books_path, encoding="utf-8") as f:
        raw = json.load(f)

    return [
        Book(
            usx_code=item["usx_code"],
            hungarian_name=item["hungarian_name"],
            abbreviation=item["abbreviation"],
            book_number=item["book_number"],
            testament=item["testament"],
            deuterocanonical=item["deuterocanonical"],
        )
        for item in raw
    ]


def _get_books_cache() -> list[Book]:
    """Get or initialize the module-level books cache."""
    global _BOOKS
    if _BOOKS is None:
        _BOOKS = load_books()
    return _BOOKS


def lookup_by_abbreviation(
    abbrev: str,
    books: list[Book] | None = None,
) -> Book | None:
    """Look up a book by its Hungarian abbreviation (case-insensitive).

    Args:
        abbrev: Hungarian abbreviation (e.g., 'Ter', 'ter', 'TER').
        books: Optional list of books to search. Uses cache if None.

    Returns:
        Book if found, None otherwise.
    """
    if books is None:
        books = _get_books_cache()

    abbrev_lower = abbrev.lower()
    for book in books:
        if book.abbreviation.lower() == abbrev_lower:
            return book
    return None


def lookup_by_usx_code(
    usx_code: str,
    books: list[Book] | None = None,
) -> Book | None:
    """Look up a book by its USX code.

    Args:
        usx_code: Paratext USX code (e.g., 'GEN', 'MRK').
        books: Optional list of books to search. Uses cache if None.

    Returns:
        Book if found, None otherwise.
    """
    if books is None:
        books = _get_books_cache()

    usx_upper = usx_code.upper()
    for book in books:
        if book.usx_code == usx_upper:
            return book
    return None


def get_all_books(books: list[Book] | None = None) -> list[Book]:
    """Return all 73 Catholic Bible books in canonical order.

    Args:
        books: Optional list of books. Uses cache if None.

    Returns:
        List of all 73 books.
    """
    if books is None:
        books = _get_books_cache()
    return books
