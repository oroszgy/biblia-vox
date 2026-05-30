"""Tests for SZIT Bible JSON text source loading and verse extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bibliavox.text.source import get_chapter_verses, get_verse_text, load_szit_json


@pytest.fixture()
def sample_data(tmp_path: Path) -> Path:
    """Create a minimal SZIT JSON sample for testing."""
    data = {
        "Genesis": {
            "1": {
                "1": "Kezdetkor teremtette Isten az eget és a földet.",
                "2": "A föld puszta volt és üres.",
                "3": "Isten szólt: Legyen világosság.",
            },
            "2": {
                "1": "Így lett kész az ég és a föld.",
            },
        },
        "Exodus": {
            "1": {
                "1": "Ezek Izrael fiai nevei.",
            },
        },
    }
    file_path = tmp_path / "H_Kaldi_SZIT.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return tmp_path


class TestLoadSzitJson:
    """Tests for load_szit_json function."""

    def test_loads_valid_json(self, sample_data: Path) -> None:
        """Should load valid JSON file and return dict."""
        result = load_szit_json(sample_data)
        assert isinstance(result, dict)
        assert "Genesis" in result

    def test_returns_dict_with_book_keys(self, sample_data: Path) -> None:
        """Should return dict with English book names as keys."""
        result = load_szit_json(sample_data)
        assert set(result.keys()) == {"Genesis", "Exodus"}

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError when file doesn't exist."""
        import bibliavox.text.source

        bibliavox.text.source._SZIT_DATA = None
        with pytest.raises(FileNotFoundError):
            load_szit_json(tmp_path)

    def test_caches_loaded_data(self, sample_data: Path) -> None:
        """Should cache loaded data for subsequent calls."""
        # Clear cache first

        import bibliavox.text.source

        bibliavox.text.source._SZIT_DATA = None

        result1 = load_szit_json(sample_data)
        result2 = load_szit_json(sample_data)
        assert result1 is result2


class TestGetChapterVerses:
    """Tests for get_chapter_verses function."""

    def test_returns_verses_for_chapter(self, sample_data: Path) -> None:
        """Should return dict of {verse_num: text} for a chapter."""
        data = load_szit_json(sample_data)
        verses = get_chapter_verses("Genesis", 1, data)
        assert verses == {
            1: "Kezdetkor teremtette Isten az eget és a földet.",
            2: "A föld puszta volt és üres.",
            3: "Isten szólt: Legyen világosság.",
        }

    def test_returns_int_keys(self, sample_data: Path) -> None:
        """Should return integer verse numbers as keys."""
        data = load_szit_json(sample_data)
        verses = get_chapter_verses("Genesis", 1, data)
        assert all(isinstance(k, int) for k in verses.keys())

    def test_raises_on_missing_book(self, sample_data: Path) -> None:
        """Should raise KeyError for non-existent book."""
        data = load_szit_json(sample_data)
        with pytest.raises(KeyError, match="NonExistent"):
            get_chapter_verses("NonExistent", 1, data)

    def test_raises_on_missing_chapter(self, sample_data: Path) -> None:
        """Should raise KeyError for non-existent chapter."""
        data = load_szit_json(sample_data)
        with pytest.raises(KeyError):
            get_chapter_verses("Genesis", 99, data)


class TestGetVerseText:
    """Tests for get_verse_text function."""

    def test_returns_specific_verse(self, sample_data: Path) -> None:
        """Should return text of a specific verse."""
        data = load_szit_json(sample_data)
        text = get_verse_text("Genesis", 1, 1, data)
        assert text == "Kezdetkor teremtette Isten az eget és a földet."

    def test_raises_on_missing_verse(self, sample_data: Path) -> None:
        """Should raise KeyError for non-existent verse."""
        data = load_szit_json(sample_data)
        with pytest.raises(KeyError):
            get_verse_text("Genesis", 1, 99, data)
