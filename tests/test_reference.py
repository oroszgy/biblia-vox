"""Tests for the reference data module (books + schema)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bibliavox.reference.books import (
    Book,
    get_all_books,
    load_books,
    lookup_by_abbreviation,
    lookup_by_usx_code,
)
from bibliavox.reference.schema import (
    BookSchema,
    get_chapter_count,
    get_verse_count,
    get_versification,
    load_versification,
)

# Test data directory (relative to repo root)
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"


@pytest.fixture
def books() -> list[Book]:
    """Load all books for testing."""
    return load_books(DATA_DIR)


@pytest.fixture
def schemas() -> list[BookSchema]:
    """Load all versification schemas for testing."""
    return load_versification(DATA_DIR)


class TestBooks:
    """Tests for the book catalog."""

    def test_load_books_returns_73_books(self, books: list[Book]) -> None:
        """Catholic Bible has exactly 73 books."""
        assert len(books) == 73

    def test_lookup_ter_returns_gen(self, books: list[Book]) -> None:
        """Hungarian abbreviation 'Ter' maps to Genesis (GEN)."""
        result = lookup_by_abbreviation("Ter", books)
        assert result is not None
        assert result.usx_code == "GEN"
        assert result.hungarian_name == "Teremtés könyve"

    def test_lookup_case_insensitive(self, books: list[Book]) -> None:
        """Abbreviation lookup is case-insensitive."""
        lower = lookup_by_abbreviation("ter", books)
        upper = lookup_by_abbreviation("TER", books)
        mixed = lookup_by_abbreviation("Ter", books)
        assert lower is not None
        assert upper is not None
        assert mixed is not None
        assert lower.usx_code == upper.usx_code == mixed.usx_code == "GEN"

    def test_lookup_unknown_returns_none(self, books: list[Book]) -> None:
        """Unknown abbreviation returns None."""
        assert lookup_by_abbreviation("XYZ", books) is None

    def test_deuterocanonical_books_present(self, books: list[Book]) -> None:
        """At least 7 deuterocanonical books are present."""
        deuterocanonical = [b for b in books if b.deuterocanonical]
        assert len(deuterocanonical) >= 7

    def test_all_books_have_usx_codes(self, books: list[Book]) -> None:
        """No book has an empty usx_code."""
        for book in books:
            assert book.usx_code, f"Empty usx_code for book: {book}"

    def test_lookup_by_usx_code(self, books: list[Book]) -> None:
        """USX code lookup works correctly."""
        result = lookup_by_usx_code("GEN", books)
        assert result is not None
        assert result.abbreviation == "Ter"

    def test_get_all_books(self, books: list[Book]) -> None:
        """get_all_books returns all 73 books."""
        all_books = get_all_books(books)
        assert len(all_books) == 73

    def test_books_have_testament_field(self, books: list[Book]) -> None:
        """All books have a valid testament field."""
        for book in books:
            assert book.testament in ("OT", "NT"), (
                f"Invalid testament for {book.usx_code}"
            )

    def test_ot_nt_counts(self, books: list[Book]) -> None:
        """OT has 46 books, NT has 27 books (73 total Catholic canon)."""
        ot = [b for b in books if b.testament == "OT"]
        nt = [b for b in books if b.testament == "NT"]
        assert len(ot) == 46
        assert len(nt) == 27


class TestVersification:
    """Tests for the versification schema."""

    def test_load_versification_has_genesis(self, schemas: list[BookSchema]) -> None:
        """Genesis exists in versification with 50 chapters."""
        gen = get_versification("GEN", schemas)
        assert gen is not None
        assert gen.chapter_count == 50

    def test_genesis_chapter1_has_31_verses(self, schemas: list[BookSchema]) -> None:
        """Genesis chapter 1 has 31 verses."""
        assert get_verse_count("GEN", 1, schemas) == 31

    def test_get_chapter_count(self, schemas: list[BookSchema]) -> None:
        """get_chapter_count returns correct values."""
        assert get_chapter_count("GEN", schemas) == 50
        assert get_chapter_count("PSA", schemas) == 150
        assert get_chapter_count("MAT", schemas) == 28

    def test_get_verse_count_psalms(self, schemas: list[BookSchema]) -> None:
        """Psalm 119 has 176 verses (longest chapter)."""
        assert get_verse_count("PSA", 119, schemas) == 176

    def test_get_versification_not_found(self, schemas: list[BookSchema]) -> None:
        """Unknown USX code returns None."""
        assert get_versification("XYZ", schemas) is None

    def test_get_chapter_count_not_found(self, schemas: list[BookSchema]) -> None:
        """Unknown USX code raises KeyError."""
        with pytest.raises(KeyError, match="XYZ"):
            get_chapter_count("XYZ", schemas)

    def test_get_verse_count_not_found_chapter(self, schemas: list[BookSchema]) -> None:
        """Invalid chapter raises KeyError."""
        with pytest.raises(KeyError, match="Chapter 999"):
            get_verse_count("GEN", 999, schemas)

    def test_all_books_have_versification(self, schemas: list[BookSchema]) -> None:
        """All 73 books have versification data."""
        assert len(schemas) == 73

    def test_esther_has_16_chapters(self, schemas: list[BookSchema]) -> None:
        """Esther (Catholic) has 16 chapters (includes deuterocanonical additions)."""
        assert get_chapter_count("EST", schemas) == 16

    def test_daniel_has_12_chapters(self, schemas: list[BookSchema]) -> None:
        """Daniel (SZIT) has 12 chapters (no deuterocanonical additions in source)."""
        assert get_chapter_count("DAN", schemas) == 12
