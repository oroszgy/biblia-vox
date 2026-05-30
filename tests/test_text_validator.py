"""Tests for Bible text verse count validation and discrepancy reporting."""

from __future__ import annotations

import json

import pytest

from bibliavox.reference.schema import BookSchema
from bibliavox.text.validator import (
    Discrepancy,
    Severity,
    generate_report,
    validate_book,
    validate_chapter,
)


@pytest.fixture()
def sample_schema() -> BookSchema:
    """Create a sample BookSchema for testing."""
    return BookSchema(
        usx_code="GEN",
        chapter_count=2,
        chapters={1: 3, 2: 2},
    )


class TestValidateChapter:
    """Tests for validate_chapter function."""

    def test_matching_verse_count(self, sample_schema: BookSchema) -> None:
        """Should return no discrepancies when verse count matches."""
        verses = {1: "verse 1", 2: "verse 2", 3: "verse 3"}
        result = validate_chapter("GEN", 1, verses, [sample_schema])
        assert result == []

    def test_mismatched_verse_count(self, sample_schema: BookSchema) -> None:
        """Should return WARNING when verse count doesn't match."""
        verses = {1: "verse 1", 2: "verse 2"}  # Expected 3, got 2
        result = validate_chapter("GEN", 1, verses, [sample_schema])
        assert len(result) == 1
        assert result[0].severity == Severity.WARNING
        assert "Verse count mismatch" in result[0].details

    def test_empty_verse_text(self, sample_schema: BookSchema) -> None:
        """Should return WARNING for empty verse text."""
        verses = {1: "verse 1", 2: "", 3: "verse 3"}
        result = validate_chapter("GEN", 1, verses, [sample_schema])
        assert len(result) == 1
        assert result[0].severity == Severity.WARNING
        assert "Empty verse text" in result[0].details

    def test_missing_book_in_schema(self) -> None:
        """Should return ERROR when book not found in schema."""
        verses = {1: "verse 1"}
        result = validate_chapter("XXX", 1, verses, [])
        assert len(result) == 1
        assert result[0].severity == Severity.ERROR
        assert "not found in versification schema" in result[0].details

    def test_missing_chapter_in_schema(self, sample_schema: BookSchema) -> None:
        """Should return ERROR when chapter not found in schema."""
        verses = {1: "verse 1"}
        result = validate_chapter("GEN", 99, verses, [sample_schema])
        assert len(result) == 1
        assert result[0].severity == Severity.ERROR
        assert "Chapter 99 not found" in result[0].details

    def test_multiple_discrepancies(self, sample_schema: BookSchema) -> None:
        """Should return multiple discrepancies when multiple issues exist."""
        verses = {1: "", 2: ""}  # Expected 3, got 2, both empty
        result = validate_chapter("GEN", 1, verses, [sample_schema])
        assert len(result) == 3  # 1 count mismatch + 2 empty verses


class TestDiscrepancy:
    """Tests for Discrepancy dataclass."""

    def test_creation(self) -> None:
        """Should create Discrepancy with all fields."""
        d = Discrepancy(
            book="GEN",
            chapter=1,
            verse=1,
            severity=Severity.WARNING,
            details="Test details",
        )
        assert d.book == "GEN"
        assert d.chapter == 1
        assert d.verse == 1
        assert d.severity == Severity.WARNING
        assert d.details == "Test details"

    def test_frozen(self) -> None:
        """Should be immutable (frozen dataclass)."""
        d = Discrepancy(
            book="GEN",
            chapter=1,
            verse=None,
            severity=Severity.ERROR,
            details="Test",
        )
        with pytest.raises(AttributeError):
            d.book = "EXO"  # type: ignore[misc]


class TestSeverity:
    """Tests for Severity enum."""

    def test_values(self) -> None:
        """Should have correct string values."""
        assert Severity.ERROR.value == "ERROR"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.INFO.value == "INFO"


class TestGenerateReport:
    """Tests for generate_report function."""

    def test_json_output(self) -> None:
        """Should return valid JSON string."""
        discrepancies = [
            Discrepancy(
                book="GEN",
                chapter=1,
                verse=None,
                severity=Severity.WARNING,
                details="Verse count mismatch: expected 3, got 2",
            ),
        ]
        report = generate_report(discrepancies)
        parsed = json.loads(report)
        assert len(parsed) == 1
        assert parsed[0]["book"] == "GEN"
        assert parsed[0]["severity"] == "WARNING"

    def test_empty_report(self) -> None:
        """Should return empty JSON array for no discrepancies."""
        report = generate_report([])
        assert json.loads(report) == []

    def test_preserves_verse_none(self) -> None:
        """Should handle verse=None (chapter-level issues)."""
        discrepancies = [
            Discrepancy(
                book="GEN",
                chapter=1,
                verse=None,
                severity=Severity.ERROR,
                details="Chapter not found",
            ),
        ]
        report = generate_report(discrepancies)
        parsed = json.loads(report)
        assert parsed[0]["verse"] is None


def test_validate_book_strict_missing_chapters_reports_error() -> None:
    schemas = [BookSchema(usx_code="GEN", chapter_count=2, chapters={1: 3, 2: 2})]
    mapping = {"Genesis": "GEN"}
    data = {
        "Genesis": {
            "1": {"1": "a", "2": "b", "3": "c"},
        }
    }

    discrepancies = validate_book(
        "GEN",
        data,
        mapping,
        schemas,
        strict_missing_chapters=True,
    )

    assert any(
        d.severity == Severity.ERROR
        and d.chapter == 2
        and "Missing chapter 2" in d.details
        for d in discrepancies
    )


def test_validate_book_strict_reports_extra_chapters_as_info() -> None:
    schemas = [BookSchema(usx_code="GEN", chapter_count=1, chapters={1: 3})]
    mapping = {"Genesis": "GEN"}
    data = {
        "Genesis": {
            "1": {"1": "a", "2": "b", "3": "c"},
            "2": {"1": "x"},
        }
    }

    discrepancies = validate_book(
        "GEN",
        data,
        mapping,
        schemas,
        strict_missing_chapters=True,
    )

    assert any(
        d.severity == Severity.INFO
        and d.chapter == 2
        and "Extra chapter 2" in d.details
        for d in discrepancies
    )
