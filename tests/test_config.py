"""Tests for the configuration module."""

from __future__ import annotations

from pathlib import Path

import pytest

from bibliavox.config import (
    BibliavoxSettings,
    get_settings,
    parse_gold_chapters,
    reset_settings,
)


class TestBibliavoxSettings:
    """Tests for BibliavoxSettings."""

    def test_default_settings(self) -> None:
        """Default settings have sensible defaults."""
        settings = BibliavoxSettings()
        assert settings.data_dir == Path("data")
        assert settings.cache_dir == Path("data/.cache")
        assert settings.reference_data_path == Path("data/reference")

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables with BIBLIAVOX_ prefix override defaults."""
        monkeypatch.setenv("BIBLIAVOX_DATA_DIR", "/custom/data")
        settings = BibliavoxSettings()
        assert settings.data_dir == Path("/custom/data")

    def test_dotenv_loading(self, tmp_path: Path) -> None:
        """Settings load from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "BIBLIAVOX_DATA_DIR=/from/dotenv\nBIBLIAVOX_CACHE_DIR=/from/dotenv/cache\n"
        )
        settings = BibliavoxSettings(_env_file=env_file)  # type: ignore
        assert settings.data_dir == Path("/from/dotenv")
        assert settings.cache_dir == Path("/from/dotenv/cache")

    def test_get_settings_returns_singleton(self) -> None:
        """get_settings() returns the same instance on repeated calls."""
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
        reset_settings()

    def test_reset_settings_creates_new_instance(self) -> None:
        """reset_settings() causes get_settings() to create a new instance."""
        reset_settings()
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2
        reset_settings()

    def test_env_prefix_is_bibliavox(self) -> None:
        """The env_prefix is BIBLIAVOX_."""
        assert BibliavoxSettings.model_config.get("env_prefix") == "BIBLIAVOX_"


class TestParseGoldChapters:
    """Tests for parse_gold_chapters()."""

    def test_default_string_parses_to_10_tuples(self) -> None:
        """Default gold chapters string parses to 10 (book, chapter) tuples."""
        default = "TIT 1,TIT 2,TIT 3,TOB 1,TOB 2,TOB 3,TOB 4,ZEP 1,ZEP 2,ZEP 3"
        result = parse_gold_chapters(default)
        assert len(result) == 10
        assert result[0] == ("TIT", 1)
        assert result[9] == ("ZEP", 3)

    def test_custom_string(self) -> None:
        """Custom string parses correctly."""
        result = parse_gold_chapters("GEN 1,GEN 2")
        assert result == [("GEN", 1), ("GEN", 2)]

    def test_strips_whitespace(self) -> None:
        """Whitespace around commas and pairs is stripped."""
        result = parse_gold_chapters("TIT 1 , TIT 2")
        assert result == [("TIT", 1), ("TIT", 2)]

    def test_invalid_format_raises_value_error(self) -> None:
        """Invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid gold chapter format"):
            parse_gold_chapters("INVALID")

    def test_invalid_chapter_number_raises_value_error(self) -> None:
        """Non-integer chapter raises ValueError."""
        with pytest.raises(ValueError, match="Invalid chapter number"):
            parse_gold_chapters("TIT abc")

    def test_empty_string_returns_empty_list(self) -> None:
        """Empty string returns empty list."""
        result = parse_gold_chapters("")
        assert result == []


class TestGoldChaptersConfig:
    """Tests for gold_chapters setting in BibliavoxSettings."""

    def test_default_gold_chapters(self) -> None:
        """Default gold_chapters setting has 10 chapters."""
        settings = BibliavoxSettings()
        chapters = parse_gold_chapters(settings.gold_chapters)
        assert len(chapters) == 10

    def test_gold_chapters_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BIBLIAVOX_GOLD_CHAPTERS env var overrides default."""
        monkeypatch.setenv("BIBLIAVOX_GOLD_CHAPTERS", "GEN 1,GEN 2")
        settings = BibliavoxSettings()
        chapters = parse_gold_chapters(settings.gold_chapters)
        assert chapters == [("GEN", 1), ("GEN", 2)]
