"""Tests for Bible text CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bibliavox.cli.text import app

runner = CliRunner()


@pytest.fixture()
def sample_data(tmp_path: Path) -> Path:
    """Create a minimal SZIT JSON sample for testing."""
    data = {
        "Genesis": {
            "1": {
                "1": "Kezdetkor teremtette Isten az eget és a földet.",
                "2": "A föld puszta volt és üres.",
            },
        },
    }
    file_path = tmp_path / "H_Kaldi_SZIT.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return tmp_path


class TestTextFetchCommand:
    """Tests for the text fetch command."""

    def test_fetch_shows_help(self) -> None:
        """Should show help when --help is passed."""
        result = runner.invoke(app, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "book" in result.output.lower()
        assert "experimental" in result.output.lower()


class TestTextInfoCommand:
    """Tests for the text info command."""

    def test_info_shows_help(self) -> None:
        """Should show help when --help is passed."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "book" in result.output.lower()


class TestTextValidateCommand:
    """Tests for the text validate command."""

    def test_validate_help_shows_strict_flag(self) -> None:
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "strict-missing-chapters" in result.output


class TestTextApp:
    """Tests for the text subcommand group."""

    def test_app_has_name(self) -> None:
        """Should have name 'text'."""
        assert app.info.name == "text"

    def test_app_has_help(self) -> None:
        """Should have help text."""
        assert app.info.help is not None
        assert len(app.info.help) > 0
