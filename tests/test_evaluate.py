"""Tests for evaluation engine module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.table import Table


class TestComputeWer:
    """Test suite for compute_wer function."""

    def test_perfect_match_returns_zero(self) -> None:
        """WER is 0.0 when reference and hypothesis are identical."""
        from bibliavox.align.evaluate import compute_wer

        assert compute_wer("hello world", "hello world") == 0.0

    def test_completely_wrong_returns_one(self) -> None:
        """WER is 1.0 when every word is wrong."""
        from bibliavox.align.evaluate import compute_wer

        # 3 reference words, all different
        wer = compute_wer("a b c", "x y z")
        assert wer == pytest.approx(1.0)

    def test_one_substitution(self) -> None:
        """WER reflects single word substitution."""
        from bibliavox.align.evaluate import compute_wer

        # 3 words, 1 error
        wer = compute_wer("the cat sat", "the dog sat")
        assert wer == pytest.approx(1 / 3, abs=0.01)

    def test_empty_reference_returns_zero(self) -> None:
        """WER is 0.0 when reference is empty (no words to get wrong)."""
        from bibliavox.align.evaluate import compute_wer

        assert compute_wer("", "hello world") == 0.0

    def test_empty_hypothesis_all_errors(self) -> None:
        """WER is 1.0 when hypothesis is empty but reference has words."""
        from bibliavox.align.evaluate import compute_wer

        assert compute_wer("hello world", "") == 1.0


class TestComputeTimestampAccuracy:
    """Test suite for compute_timestamp_accuracy function."""

    def test_perfect_timestamps(self) -> None:
        """Zero deviation when timestamps match exactly."""
        from bibliavox.align.evaluate import compute_timestamp_accuracy

        predicted = [{"start": 1.0, "end": 2.0}, {"start": 3.0, "end": 4.0}]
        gold = [{"start": 1.0, "end": 2.0}, {"start": 3.0, "end": 4.0}]

        result = compute_timestamp_accuracy(predicted, gold)
        assert result["mean_start_deviation"] == pytest.approx(0.0)
        assert result["mean_end_deviation"] == pytest.approx(0.0)

    def test_constant_offset(self) -> None:
        """Mean deviation reflects constant offset."""
        from bibliavox.align.evaluate import compute_timestamp_accuracy

        predicted = [{"start": 1.5, "end": 2.5}, {"start": 3.5, "end": 4.5}]
        gold = [{"start": 1.0, "end": 2.0}, {"start": 3.0, "end": 4.0}]

        result = compute_timestamp_accuracy(predicted, gold)
        assert result["mean_start_deviation"] == pytest.approx(0.5)
        assert result["mean_end_deviation"] == pytest.approx(0.5)

    def test_max_deviation(self) -> None:
        """Max deviation captures largest outlier."""
        from bibliavox.align.evaluate import compute_timestamp_accuracy

        predicted = [{"start": 1.0, "end": 2.0}, {"start": 5.0, "end": 6.0}]
        gold = [{"start": 1.0, "end": 2.0}, {"start": 3.0, "end": 4.0}]

        result = compute_timestamp_accuracy(predicted, gold)
        assert result["max_start_deviation"] == pytest.approx(2.0)
        assert result["max_end_deviation"] == pytest.approx(2.0)


class TestCachedResults:
    """Test suite for load_cached_result and save_cached_result."""

    def test_save_creates_correct_path(self, tmp_path: Path) -> None:
        """save_cached_result writes to data/aligned/{model}/{USX}/{chapter}.json."""
        from bibliavox.align.evaluate import save_cached_result

        result = [{"verse_id": "1", "start_sec": 0.0, "end_sec": 1.0}]
        path = save_cached_result(result, "faster-whisper", "GEN", 1, tmp_path)

        expected = tmp_path / "aligned" / "faster-whisper" / "GEN" / "001.json"
        assert path == expected
        assert path.exists()

        with open(path) as f:
            loaded = json.load(f)
        assert loaded == result

    def test_load_returns_cached_result(self, tmp_path: Path) -> None:
        """load_cached_result returns previously saved result."""
        from bibliavox.align.evaluate import load_cached_result, save_cached_result

        result = [{"verse_id": "1", "start_sec": 0.0, "end_sec": 1.0}]
        save_cached_result(result, "faster-whisper", "GEN", 1, tmp_path)

        loaded = load_cached_result("faster-whisper", "GEN", 1, tmp_path)
        assert loaded == result

    def test_load_returns_none_when_not_cached(self, tmp_path: Path) -> None:
        """load_cached_result returns None when no cached file exists."""
        from bibliavox.align.evaluate import load_cached_result

        assert load_cached_result("faster-whisper", "GEN", 99, tmp_path) is None

    def test_cache_never_auto_invalidates(self, tmp_path: Path) -> None:
        """Cache returns existing file as-is, never auto-invalidates (D-37)."""
        from bibliavox.align.evaluate import load_cached_result, save_cached_result

        # Save stale result
        stale = [{"verse_id": "1", "start_sec": 0.0, "end_sec": 1.0}]
        save_cached_result(stale, "model", "GEN", 1, tmp_path)

        # Load should return stale result, not None
        loaded = load_cached_result("model", "GEN", 1, tmp_path)
        assert loaded == stale


class TestBuildComparisonTable:
    """Test suite for build_comparison_table function."""

    def test_returns_rich_table(self) -> None:
        """build_comparison_table returns a Rich Table object."""
        from bibliavox.align.evaluate import build_comparison_table

        results = [
            {
                "model": "model-a",
                "book": "GEN",
                "chapter": 1,
                "wer": 0.1,
                "mean_start_deviation": 0.5,
                "mean_end_deviation": 0.3,
                "avg_confidence": 85.0,
                "cost_usd": 0.0,
                "time_sec": 10.0,
                "aligned_verses": 30,
                "total_verses": 31,
            },
        ]

        table = build_comparison_table(results)
        assert isinstance(table, Table)

    def test_table_has_model_rows(self) -> None:
        """Table contains one row per model result."""
        from bibliavox.align.evaluate import build_comparison_table

        results = [
            {
                "model": f"model-{i}",
                "book": "GEN",
                "chapter": 1,
                "wer": 0.1 * i,
                "mean_start_deviation": 0.5,
                "mean_end_deviation": 0.3,
                "avg_confidence": 85.0,
                "cost_usd": 0.0,
                "time_sec": 10.0,
                "aligned_verses": 30,
                "total_verses": 31,
            }
            for i in range(3)
        ]

        table = build_comparison_table(results)
        # Rich Table rows count: header + data rows
        assert len(table.rows) == 3


class TestSaveEvaluationReport:
    """Test suite for save_evaluation_report function."""

    def test_saves_jsonl_and_summary(self, tmp_path: Path) -> None:
        """save_evaluation_report creates both JSONL and summary JSON files."""
        from bibliavox.align.evaluate import save_evaluation_report

        results = [
            {
                "model": "model-a",
                "book": "GEN",
                "chapter": 1,
                "wer": 0.1,
                "mean_start_deviation": 0.5,
                "mean_end_deviation": 0.3,
                "avg_confidence": 85.0,
                "cost_usd": 0.0,
                "time_sec": 10.0,
                "aligned_verses": 30,
                "total_verses": 31,
            }
        ]

        jsonl_path, summary_path = save_evaluation_report(results, tmp_path)

        assert jsonl_path.exists()
        assert summary_path.exists()
        assert jsonl_path.suffix == ".jsonl"
        assert summary_path.suffix == ".json"

        # Verify JSONL content
        with open(jsonl_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 1
        assert lines[0]["model"] == "model-a"

        # Verify summary content
        with open(summary_path) as f:
            summary = json.load(f)
        assert "results" in summary
