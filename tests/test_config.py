"""Tests for the configuration module."""

from __future__ import annotations

from pathlib import Path

import pytest

from bibliavox.config import BibliavoxSettings, get_settings, reset_settings


class TestBibliavoxSettings:
    """Tests for BibliavoxSettings."""

    def test_default_settings(self) -> None:
        """Default settings have sensible defaults."""
        settings = BibliavoxSettings()
        assert settings.data_dir == Path("data")
        assert settings.cache_dir == Path("data/.cache")
        assert settings.reference_data_path == Path("data/reference")
        assert settings.szentiras_api_key == ""

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables with BIBLIAVOX_ prefix override defaults."""
        monkeypatch.setenv("BIBLIAVOX_DATA_DIR", "/custom/data")
        monkeypatch.setenv("BIBLIAVOX_SZENTIRAS_API_KEY", "test-key-123")
        settings = BibliavoxSettings()
        assert settings.data_dir == Path("/custom/data")
        assert settings.szentiras_api_key == "test-key-123"

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
