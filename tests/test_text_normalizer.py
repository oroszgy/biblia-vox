"""Tests for Bible text normalization pipeline."""

from __future__ import annotations

import pytest

from bibliavox.text.normalizer import normalize_chapter, normalize_text, normalize_verse


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_whitespace_collapse(self) -> None:
        """Should collapse multiple spaces to single space."""
        assert normalize_text("  Hello   world  ") == "Hello world"

    def test_nfc_normalization(self) -> None:
        """Should normalize to NFC form."""
        # árvíztűrő is already NFC
        assert normalize_text("árvíztűrő") == "árvíztűrő"

    def test_nfd_to_nfc(self) -> None:
        """Should convert NFD input to NFC form."""
        import unicodedata

        nfd_text = unicodedata.normalize("NFD", "árvíztűrő")
        nfc_text = unicodedata.normalize("NFC", "árvíztűrő")
        assert normalize_text(nfd_text) == nfc_text

    def test_line_ending_normalization(self) -> None:
        """Should normalize \\r\\n to \\n."""
        assert normalize_text("line1\r\nline2") == "line1\nline2"

    def test_carriage_return_normalization(self) -> None:
        """Should normalize \\r to \\n."""
        assert normalize_text("line1\rline2") == "line1\nline2"

    def test_empty_string_preserved(self) -> None:
        """Should preserve empty strings."""
        assert normalize_text("") == ""

    def test_whitespace_only(self) -> None:
        """Should strip whitespace-only strings."""
        assert normalize_text("   ") == ""

    def test_leading_trailing_whitespace(self) -> None:
        """Should strip leading/trailing whitespace."""
        assert normalize_text("  hello  ") == "hello"

    def test_hungarian_text(self) -> None:
        """Should handle Hungarian diacritics correctly."""
        text = "Kezdetkor teremtette Isten az eget és a földet."
        assert normalize_text(text) == text


class TestNormalizeVerse:
    """Tests for normalize_verse function."""

    def test_normalizes_verse_text(self) -> None:
        """Should normalize a single verse text."""
        assert normalize_verse("  Hello   world  ") == "Hello world"

    def test_preserves_verse_content(self) -> None:
        """Should preserve verse content after normalization."""
        verse = "Kezdetkor teremtette Isten az eget és a földet."
        assert normalize_verse(verse) == verse


class TestNormalizeChapter:
    """Tests for normalize_chapter function."""

    def test_normalizes_all_verses(self) -> None:
        """Should normalize all verses in a chapter."""
        verses = {
            1: "  First   verse  ",
            2: "  Second   verse  ",
            3: "  Third   verse  ",
        }
        result = normalize_chapter(verses)
        assert result == {
            1: "First verse",
            2: "Second verse",
            3: "Third verse",
        }

    def test_preserves_verse_numbers(self) -> None:
        """Should preserve verse numbers as keys."""
        verses = {1: "verse 1", 2: "verse 2"}
        result = normalize_chapter(verses)
        assert set(result.keys()) == {1, 2}

    def test_empty_chapter(self) -> None:
        """Should handle empty chapter dict."""
        assert normalize_chapter({}) == {}
