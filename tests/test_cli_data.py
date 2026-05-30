"""Tests for data coverage CLI command."""

from __future__ import annotations

from typer.testing import CliRunner

from bibliavox.main import app

runner = CliRunner()


def test_data_coverage_help_shows_flags() -> None:
    result = runner.invoke(app, ["data", "coverage", "--help"])
    assert result.exit_code == 0
    assert "allow-deuterocanon" in result.output
    assert "allow-known-source" in result.output


def test_data_coverage_json_exit_zero_when_complete(monkeypatch) -> None:
    monkeypatch.setattr(
        "bibliavox.cli.data.audit_coverage",
        lambda **_: {
            "summary": {
                "books_scoped": 66,
                "text_missing_total": 0,
                "audio_raw_missing_total": 0,
                "audio_wav_missing_total": 0,
                "audio_index_missing_total": 0,
                "audio_meta_missing_total": 0,
                "unresolved": {
                    "text_missing": 0,
                    "audio_raw_missing": 0,
                    "audio_wav_missing": 0,
                    "audio_index_missing": 0,
                    "audio_meta_missing": 0,
                },
            },
            "complete": True,
            "remote_audio_error": None,
        },
    )

    result = runner.invoke(app, ["data", "coverage", "--json"])
    assert result.exit_code == 0
    assert '"complete": true' in result.output


def test_data_coverage_exit_nonzero_when_incomplete(monkeypatch) -> None:
    monkeypatch.setattr(
        "bibliavox.cli.data.audit_coverage",
        lambda **_: {
            "summary": {
                "books_scoped": 66,
                "text_missing_total": 1,
                "audio_raw_missing_total": 0,
                "audio_wav_missing_total": 0,
                "audio_index_missing_total": 0,
                "audio_meta_missing_total": 0,
                "unresolved": {
                    "text_missing": 1,
                    "audio_raw_missing": 0,
                    "audio_wav_missing": 0,
                    "audio_index_missing": 0,
                    "audio_meta_missing": 0,
                },
            },
            "complete": False,
            "remote_audio_error": None,
        },
    )

    result = runner.invoke(app, ["data", "coverage"])
    assert result.exit_code == 1
    assert "Coverage summary" in result.output
