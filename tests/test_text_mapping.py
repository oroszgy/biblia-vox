"""Tests for English book name to USX code mapping."""

from __future__ import annotations

import pytest

from bibliavox.text.mapping import english_to_usx, load_book_mapping


class TestLoadBookMapping:
    """Tests for load_book_mapping function."""

    def test_returns_dict(self) -> None:
        """Should return a dict mapping English names to USX codes."""
        mapping = load_book_mapping()
        assert isinstance(mapping, dict)

    def test_maps_genesis(self) -> None:
        """Should map Genesis to GEN."""
        mapping = load_book_mapping()
        assert mapping.get("Genesis") == "GEN"

    def test_maps_exodus(self) -> None:
        """Should map Exodus to EXO."""
        mapping = load_book_mapping()
        assert mapping.get("Exodus") == "EXO"

    def test_maps_new_testament(self) -> None:
        """Should map New Testament books correctly."""
        mapping = load_book_mapping()
        assert mapping.get("Matthew") == "MAT"
        assert mapping.get("Mark") == "MRK"
        assert mapping.get("Luke") == "LUK"
        assert mapping.get("John") == "JHN"

    def test_maps_numbered_books(self) -> None:
        """Should map numbered books like 1Samuel, 2Samuel."""
        mapping = load_book_mapping()
        assert mapping.get("1Samuel") == "1SA"
        assert mapping.get("2Samuel") == "2SA"
        assert mapping.get("1Kings") == "1KI"
        assert mapping.get("2Kings") == "2KI"

    def test_maps_deuterocanonical_books(self) -> None:
        """Should map all 7 deuterocanonical books."""
        mapping = load_book_mapping()
        assert mapping.get("Tobit") == "TOB"
        assert mapping.get("Judith") == "JDT"
        assert mapping.get("Wisdom") == "WIS"
        assert mapping.get("Sirach") == "SIR"
        assert mapping.get("Baruch") == "BAR"
        assert mapping.get("1Maccabees") == "1MA"
        assert mapping.get("2Maccabees") == "2MA"

    def test_contains_all_73_books(self) -> None:
        """Should contain mappings for all 73 Catholic books."""
        mapping = load_book_mapping()
        assert len(mapping) == 73

    def test_maps_song_of_songs(self) -> None:
        """Should map SongOfSongs (not Song of Solomon) to SNG."""
        mapping = load_book_mapping()
        assert mapping.get("SongOfSongs") == "SNG"


class TestEnglishToUsx:
    """Tests for english_to_usx function."""

    def test_returns_usx_code(self) -> None:
        """Should return USX code for known English name."""
        result = english_to_usx("Genesis")
        assert result == "GEN"

    def test_raises_on_unknown_name(self) -> None:
        """Should raise KeyError for unknown English name."""
        with pytest.raises(KeyError):
            english_to_usx("NonExistentBook")

    def test_maps_deuterocanonical(self) -> None:
        """Should map deuterocanonical book names."""
        assert english_to_usx("Tobit") == "TOB"
        assert english_to_usx("Judith") == "JDT"
        assert english_to_usx("Wisdom") == "WIS"
        assert english_to_usx("Sirach") == "SIR"
        assert english_to_usx("Baruch") == "BAR"
        assert english_to_usx("1Maccabees") == "1MA"
        assert english_to_usx("2Maccabees") == "2MA"

    def test_uses_cache_when_mapping_none(self) -> None:
        """Should use cached mapping when mapping parameter is None."""
        result1 = english_to_usx("Genesis")
        result2 = english_to_usx("Genesis")
        assert result1 == result2 == "GEN"
