"""Tests for versification schema corrections in Phase 2.5.

These tests verify that versification.json matches the actual SZIT source data
for books with known discrepancies (DAN, MAL, and off-by-one books).
"""

from __future__ import annotations

import pytest

from bibliavox.reference.schema import get_versification, load_versification


@pytest.fixture()
def schemas():
    """Load versification schemas."""
    return load_versification()


class TestDanielFixes:
    """Tests for Daniel schema corrections."""

    def test_dan_has_12_chapters(self, schemas):
        """DAN should have 12 chapters in SZIT (not 14 with deuterocanonical additions)."""
        dan = get_versification("DAN", schemas)
        assert dan is not None
        assert dan.chapter_count == 12

    def test_dan_3_has_30_verses(self, schemas):
        """DAN 3 should have 30 verses (not 91 with deuterocanonical additions)."""
        dan = get_versification("DAN", schemas)
        assert dan is not None
        assert dan.chapters[3] == 30

    def test_dan_has_no_deuterocanonical_chapters(self, schemas):
        """DAN should not have chapters 13 or 14 (Susanna, Bel)."""
        dan = get_versification("DAN", schemas)
        assert dan is not None
        assert 13 not in dan.chapters
        assert 14 not in dan.chapters

    def test_dan_6_has_28_verses(self, schemas):
        """DAN 6 should have 28 verses (not 29)."""
        dan = get_versification("DAN", schemas)
        assert dan is not None
        assert dan.chapters[6] == 28


class TestMalachiFixes:
    """Tests for Malachi schema corrections."""

    def test_mal_has_4_chapters(self, schemas):
        """MAL should have 4 chapters (not 3)."""
        mal = get_versification("MAL", schemas)
        assert mal is not None
        assert mal.chapter_count == 4
        assert 4 in mal.chapters

    def test_mal_4_has_6_verses(self, schemas):
        """MAL chapter 4 should have 6 verses."""
        mal = get_versification("MAL", schemas)
        assert mal is not None
        assert mal.chapters[4] == 6


class TestOffByOneFixes:
    """Tests for off-by-one verse count corrections."""

    def test_1sa_20_has_42_verses(self, schemas):
        """1SA 20 should have 42 verses (not 43)."""
        book = get_versification("1SA", schemas)
        assert book is not None
        assert book.chapters[20] == 42

    def test_jon_1_has_17_verses(self, schemas):
        """JON 1 should have 17 verses (not 16)."""
        book = get_versification("JON", schemas)
        assert book is not None
        assert book.chapters[1] == 17

    def test_nam_1_has_15_verses(self, schemas):
        """NAM 1 should have 15 verses (not 14)."""
        book = get_versification("NAM", schemas)
        assert book is not None
        assert book.chapters[1] == 15

    def test_hab_2_has_20_verses(self, schemas):
        """HAB 2 should have 20 verses (not 17)."""
        book = get_versification("HAB", schemas)
        assert book is not None
        assert book.chapters[2] == 20

    def test_2co_13_has_14_verses(self, schemas):
        """2CO 13 should have 14 verses (not 13)."""
        book = get_versification("2CO", schemas)
        assert book is not None
        assert book.chapters[13] == 14

    def test_3jn_1_has_14_verses(self, schemas):
        """3JN 1 should have 14 verses (not 15)."""
        book = get_versification("3JN", schemas)
        assert book is not None
        assert book.chapters[1] == 14


class TestSchemaIntegrity:
    """General schema integrity tests."""

    def test_all_szit_books_have_versification(self, schemas):
        """All 66 SZIT books should have versification entries."""
        # SZIT has 66 books (no deuterocanonical in source)
        schema_codes = {s.usx_code for s in schemas}
        # At minimum, the schema should have entries for all standard books
        assert len(schemas) >= 66

    def test_no_zero_verse_counts(self, schemas):
        """No chapter should have 0 or negative verse count."""
        for schema in schemas:
            for ch, count in schema.chapters.items():
                assert count > 0, f"{schema.usx_code} chapter {ch} has {count} verses"

    def test_no_zero_chapter_counts(self, schemas):
        """No book should have 0 or negative chapter count."""
        for schema in schemas:
            assert schema.chapter_count > 0, (
                f"{schema.usx_code} has {schema.chapter_count} chapters"
            )
