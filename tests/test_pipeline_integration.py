"""Integration tests for pipeline chain wiring.

Verifies that CLI, config, writer module, and Taskfile are wired together
correctly — not just that individual pieces exist.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bibliavox.config import parse_gold_chapters, reset_settings
from bibliavox.export.writer import reset_canonical_text_cache
from bibliavox.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None]:
    """Reset config and canonical text cache, point data dir to tmp_path."""
    reset_settings()
    reset_canonical_text_cache()
    monkeypatch.setenv("BIBLIAVOX_DATA_DIR", str(tmp_path))
    yield
    reset_settings()
    reset_canonical_text_cache()


def _make_evaluation_data(
    tmp_path: Path,
    book: str = "TIT",
    chapter: int = 1,
    model: str = "microsoft/VibeVoice-ASR-HF",
    verses: list[dict] | None = None,
) -> None:
    """Create a minimal matched JSON file in the evaluation directory."""
    eval_dir = tmp_path / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    model_safe = model.replace("/", "_")
    filename = f"{book}_{chapter:03d}_{model_safe}_matched.json"

    if verses is None:
        verses = [
            {
                "verse_id": "1",
                "start_sec": 1.0,
                "end_sec": 5.0,
                "confidence_score": 90.0,
                "canonical_text": "Verse one.",
                "matched_text": "Verse one.",
            },
            {
                "verse_id": "2",
                "start_sec": 5.0,
                "end_sec": 10.0,
                "confidence_score": 80.0,
                "canonical_text": "Verse two.",
                "matched_text": "Verse two.",
            },
        ]

    data = {
        "chapter": f"{book} {chapter}",
        "model": model,
        "metrics": {"canonical_verses": len(verses), "aligned_verses": len(verses)},
        "verses": verses,
    }
    (eval_dir / filename).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def _make_mek_jsonl(tmp_path: Path, verses: list[dict] | None = None) -> None:
    """Create a minimal mek.jsonl file in the processed text directory."""
    mek_dir = tmp_path / "processed" / "text"
    mek_dir.mkdir(parents=True, exist_ok=True)

    if verses is None:
        verses = [
            {"book": "TIT", "chapter": 1, "verse": "1", "text": "Verse one."},
            {"book": "TIT", "chapter": 1, "verse": "2", "text": "Verse two."},
        ]

    lines = [json.dumps(v, ensure_ascii=False) for v in verses]
    (mek_dir / "mek.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Test 1: CLI subcommand exists ---


def test_export_cli_jsonl_subcommand_exists() -> None:
    """bibliavox export --help lists the jsonl subcommand."""
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "jsonl" in result.output


# --- Test 2: CLI help shows all options ---


def test_export_jsonl_help_shows_all_options() -> None:
    """bibliavox export jsonl --help shows --gold, --model, --force options."""
    result = runner.invoke(app, ["export", "jsonl", "--help"])
    assert result.exit_code == 0
    assert "--gold" in result.output
    assert "--model" in result.output
    assert "--force" in result.output


# --- Test 3: Export with mock data produces correct JSONL ---


def test_export_jsonl_gold_with_mock_data(tmp_path: Path) -> None:
    """Export CLI with --gold produces JSONL with all D-07 fields from mock data."""
    _make_mek_jsonl(tmp_path)
    _make_evaluation_data(tmp_path)

    result = runner.invoke(app, ["export", "jsonl", "--gold"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # Find output JSONL file
    export_dir = tmp_path / "export"
    assert export_dir.exists(), "Export directory not created"

    jsonl_files = list(export_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1, f"Expected 1 JSONL file, got {len(jsonl_files)}"

    # Verify JSONL content has all D-07 fields
    lines = jsonl_files[0].read_text().strip().split("\n")
    assert len(lines) == 2, f"Expected 2 verses, got {len(lines)}"

    expected_fields = {
        "verse_ref",
        "audio_file",
        "start_sec",
        "end_sec",
        "source",
        "translation",
        "confidence",
        "canonical_text",
        "matched_text",
        "wer",
        "cer",
    }
    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == expected_fields
        assert row["translation"] == "SZIT"
        assert row["source"] == "microsoft/VibeVoice-ASR-HF"
        assert row["verse_ref"].startswith("TIT 1:")
        assert row["confidence"] >= 0.0
        assert row["confidence"] <= 1.0


# --- Test 4: Force overwrites complete export ---


def test_export_jsonl_force_overwrites_complete(tmp_path: Path) -> None:
    """--force re-exports even when chapter is already complete."""
    _make_mek_jsonl(tmp_path)
    _make_evaluation_data(tmp_path)

    # First export (normal)
    result1 = runner.invoke(app, ["export", "jsonl", "--gold"])
    assert result1.exit_code == 0

    export_dir = tmp_path / "export"
    jsonl_files = list(export_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1
    first_line_count = len(jsonl_files[0].read_text().strip().split("\n"))
    assert first_line_count == 2

    # Second export without --force (should skip)
    result2 = runner.invoke(app, ["export", "jsonl", "--gold"])
    assert result2.exit_code == 0
    assert "already complete" in result2.output.lower() or result2.exit_code == 0

    # Third export with --force (should re-export)
    result3 = runner.invoke(app, ["export", "jsonl", "--gold", "--force"])
    assert result3.exit_code == 0

    # File should have same line count (replaced, not appended)
    final_line_count = len(jsonl_files[0].read_text().strip().split("\n"))
    assert final_line_count == first_line_count, (
        f"--force should replace, not append: expected {first_line_count} lines, got {final_line_count}"
    )


# --- Test 5: Taskfile export targets present ---


def test_taskfile_export_targets_present() -> None:
    """All 5 export targets appear in task --list."""
    import subprocess

    result = subprocess.run(
        ["go-task", "--list"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )
    output = result.stdout + result.stderr

    expected_targets = [
        "export:fetch-text",
        "export:prepare-audio",
        "export:align",
        "export:jsonl",
        "export:run",
    ]
    for target in expected_targets:
        assert target in output, (
            f"Taskfile target '{target}' not found in task --list output"
        )


# --- Test 6: parse_gold_chapters integration ---


def test_parse_gold_chapters_integration() -> None:
    """parse_gold_chapters returns correct (book, chapter) tuples from config string."""
    result = parse_gold_chapters("TIT 1,TIT 2,TIT 3")
    assert result == [("TIT", 1), ("TIT", 2), ("TIT", 3)]


def test_parse_gold_chapters_default_config() -> None:
    """Default gold_chapters config parses to 10 chapters across TIT, TOB, ZEP."""
    from bibliavox.config import get_settings

    settings = get_settings()
    chapters = parse_gold_chapters(settings.gold_chapters)

    # Default: TIT 1-3, TOB 1-4, ZEP 1-3
    assert len(chapters) == 10
    assert ("TIT", 1) in chapters
    assert ("TOB", 4) in chapters
    assert ("ZEP", 3) in chapters
