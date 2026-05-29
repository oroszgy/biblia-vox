"""BibliaVox configuration using Pydantic Settings.

Loads configuration from environment variables and .env files.
All settings use the BIBLIAVOX_ prefix.

Usage:
    from bibliavox.config import get_settings

    settings = get_settings()
    print(settings.data_dir)  # Path("data")
    print(settings.szentiras_api_key)  # "" (empty by default)
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BibliavoxSettings(BaseSettings):
    """Application settings with .env file support.

    Environment variables use the BIBLIAVOX_ prefix:
    - BIBLIAVOX_DATA_DIR
    - BIBLIAVOX_CACHE_DIR
    - BIBLIAVOX_REFERENCE_DATA_PATH
    - BIBLIAVOX_SZENTIRAS_API_KEY
    """

    model_config = SettingsConfigDict(
        env_prefix="BIBLIAVOX_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Paths
    data_dir: Path = Path("data")
    """Root data directory for all pipeline artifacts."""

    cache_dir: Path = Path("data/.cache")
    """Cache directory for intermediate artifacts (emissions, etc.)."""

    reference_data_path: Path = Path("data/reference")
    """Path to the reference data directory (books.json, versification.json)."""

    # API keys
    szentiras_api_key: str = ""
    """API key for szentiras.eu. Empty by default (requires manual setup)."""

    # Model/audio/concurrency settings deferred to later phases


# Module-level singleton
_settings: BibliavoxSettings | None = None


def get_settings() -> BibliavoxSettings:
    """Get the singleton BibliavoxSettings instance.

    Creates a new instance on first call, returns cached instance on subsequent calls.
    Use reset_settings() to force re-creation (useful in tests).
    """
    global _settings
    if _settings is None:
        _settings = BibliavoxSettings()
    return _settings


def reset_settings() -> None:
    """Reset the singleton settings instance.

    Next call to get_settings() will create a fresh instance.
    Useful in tests that need to test different configurations.
    """
    global _settings
    _settings = None
