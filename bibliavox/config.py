"""BibliaVox configuration using Pydantic Settings.

Loads configuration from environment variables and .env files.
All settings use the BIBLIAVOX_ prefix.

Usage:
    from bibliavox.config import get_settings

    settings = get_settings()
    print(settings.data_dir)  # Path("data")
"""

from __future__ import annotations

from pathlib import Path

from typing import Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """Configuration for a single alignment model."""

    id: str
    """Repository ID or path to the model."""
    type: Literal["faster-whisper", "vibevoice", "ctc"]
    """Type of the model for selecting the appropriate pipeline."""


class ModelGauntletSettings(BaseModel):
    """Settings for the model gauntlet execution."""

    models: list[ModelConfig] = [
        ModelConfig(id="systran/faster-whisper-large-v3", type="faster-whisper"),
        ModelConfig(id="microsoft/VibeVoice-ASR-HF", type="vibevoice"),
        ModelConfig(id="sarpba/wav2vec2-large-xlsr-53-hungarian", type="ctc"),
    ]


class BibliavoxSettings(BaseSettings):
    """Application settings with .env file support.

    Environment variables use the BIBLIAVOX_ prefix:
    - BIBLIAVOX_DATA_DIR
    - BIBLIAVOX_CACHE_DIR
    - BIBLIAVOX_REFERENCE_DATA_PATH
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

    models_dir: Path = Path("data/models")
    """Directory for downloaded model weights."""

    gauntlet: ModelGauntletSettings = ModelGauntletSettings()
    """Configuration for the model gauntlet."""

    # Gold chapter configuration (D-12)
    gold_chapters: str = "TIT 1,TIT 2,TIT 3,TOB 1,TOB 2,TOB 3,TOB 4,ZEP 1,ZEP 2,ZEP 3"
    """Comma-separated list of BOOK CHAPTER pairs for gold subset. Override via BIBLIAVOX_GOLD_CHAPTERS."""

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


def parse_gold_chapters(raw: str) -> list[tuple[str, int]]:
    """Parse gold chapters string into list of (book, chapter) tuples.

    Args:
        raw: Comma-separated string like "TIT 1,TIT 2,GEN 3"

    Returns:
        List of (book_code, chapter_number) tuples

    Raises:
        ValueError: If format is invalid (not "BOOK CHAPTER" pairs)
    """
    chapters: list[tuple[str, int]] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split()
        if len(parts) != 2:
            raise ValueError(
                f"Invalid gold chapter format: {pair!r}. Expected 'BOOK CHAPTER'."
            )
        try:
            chapter_num = int(parts[1])
        except ValueError:
            raise ValueError(
                f"Invalid chapter number in gold chapter: {pair!r}. Chapter must be an integer."
            ) from None
        chapters.append((parts[0], chapter_num))
    return chapters
