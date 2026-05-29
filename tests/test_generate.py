"""Tests for the reference data generation module."""

from __future__ import annotations

from bibliavox.reference.generate import (
    BOOK_METADATA,
    BOOK_NUMBERS,
    parse_gepi,
)


class TestConstants:
    """Tests for generation constants."""

    def test_book_metadata_has_73_entries(self) -> None:
        """BOOK_METADATA has exactly 73 Catholic books."""
        assert len(BOOK_METADATA) == 73

    def test_book_numbers_has_73_entries(self) -> None:
        """BOOK_NUMBERS has exactly 73 entries."""
        assert len(BOOK_NUMBERS) == 73

    def test_metadata_keys_match_numbers(self) -> None:
        """All USX codes in BOOK_METADATA have corresponding BOOK_NUMBERS."""
        metadata_codes = {m["usx_code"] for m in BOOK_METADATA}
        number_codes = set(BOOK_NUMBERS.keys())
        assert metadata_codes == number_codes

    def test_ot_nt_counts(self) -> None:
        """OT has 46 books, NT has 27 books (73 total Catholic canon)."""
        ot = [m for m in BOOK_METADATA if m["testament"] == "OT"]
        nt = [m for m in BOOK_METADATA if m["testament"] == "NT"]
        assert len(ot) == 46
        assert len(nt) == 27

    def test_deuterocanonical_count(self) -> None:
        """At least 7 deuterocanonical books are present."""
        deutero = [m for m in BOOK_METADATA if m["deuterocanonical"]]
        assert len(deutero) >= 7

    def test_genesis_is_101(self) -> None:
        """Genesis has book number 101 (gepi encoding)."""
        assert BOOK_NUMBERS["GEN"] == 101

    def test_matthew_is_401(self) -> None:
        """Matthew has book number 401 (NT starts at 400)."""
        assert BOOK_NUMBERS["MAT"] == 401


class TestParseGepi:
    """Tests for the gepi code parser."""

    def test_parse_genesis_1_31(self) -> None:
        """10100103100 -> (101, 1, 31) — Genesis chapter 1, verse 31."""
        assert parse_gepi("10100103100") == (101, 1, 31)

    def test_parse_psalms_119_1(self) -> None:
        """12311900100 -> (123, 119, 1) — Psalm 119, verse 1."""
        assert parse_gepi("12311900100") == (123, 119, 1)

    def test_parse_matthew_1_1(self) -> None:
        """40100100100 -> (401, 1, 1) — Matthew chapter 1, verse 1."""
        assert parse_gepi("40100100100") == (401, 1, 1)
