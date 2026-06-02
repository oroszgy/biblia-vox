"""Evaluation engine for comparing alignment approaches.

Computes WER, timestamp accuracy, confidence scores, and cost metrics.
Produces JSONL (machine-readable) and Rich table (CLI display) per D-30.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from rich.table import Table

logger = logging.getLogger(__name__)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate between reference and hypothesis text.

    Uses simple edit distance at word level.
    Returns WER as float (0.0 = perfect match, 1.0 = completely wrong).
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    n = len(ref_words)
    if n == 0:
        return 0.0

    m = len(hyp_words)

    # Wagner-Fischer edit distance at word level
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,  # deletion
                    d[i][j - 1] + 1,  # insertion
                    d[i - 1][j - 1] + 1,  # substitution
                )

    return d[n][m] / n


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate between reference and hypothesis text.

    Uses edit distance at character level.
    Returns CER as float (0.0 = perfect match, 1.0 = completely wrong).
    """
    ref_chars = list(reference)
    hyp_chars = list(hypothesis)

    n = len(ref_chars)
    if n == 0:
        return 0.0

    m = len(hyp_chars)

    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,
                    d[i][j - 1] + 1,
                    d[i - 1][j - 1] + 1,
                )

    return d[n][m] / n


def compute_timestamp_accuracy(
    predicted: list[dict[str, Any]],
    gold: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute timestamp accuracy metrics between predicted and gold alignments.

    Returns dict with:
    - "mean_start_deviation": average |predicted.start - gold.start|
    - "mean_end_deviation": average |predicted.end - gold.end|
    - "max_start_deviation": max |predicted.start - gold.start|
    - "max_end_deviation": max |predicted.end - gold.end|
    """
    if not predicted or not gold:
        return {
            "mean_start_deviation": 0.0,
            "mean_end_deviation": 0.0,
            "max_start_deviation": 0.0,
            "max_end_deviation": 0.0,
        }

    n = min(len(predicted), len(gold))
    start_devs = [abs(predicted[i]["start"] - gold[i]["start"]) for i in range(n)]
    end_devs = [abs(predicted[i]["end"] - gold[i]["end"]) for i in range(n)]

    return {
        "mean_start_deviation": sum(start_devs) / n,
        "mean_end_deviation": sum(end_devs) / n,
        "max_start_deviation": max(start_devs),
        "max_end_deviation": max(end_devs),
    }


def load_cached_result(
    model: str,
    book: str,
    chapter: int,
    data_dir: Path,
) -> list[dict[str, Any]] | None:
    """Load cached alignment result per D-35, D-36, D-37.

    Cache path: data/aligned/{model}/{USX}/{chapter}.json
    Never auto-invalidates — user must manually delete to re-run.
    """
    cache_path = data_dir / "aligned" / model / book / f"{chapter:03d}.json"
    if not cache_path.exists():
        return None

    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cached_result(
    result: list[dict[str, Any]],
    model: str,
    book: str,
    chapter: int,
    data_dir: Path,
) -> Path:
    """Save alignment result to cache per D-36.

    Cache path: data/aligned/{model}/{USX}/{chapter}.json
    """
    cache_path = data_dir / "aligned" / model / book / f"{chapter:03d}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return cache_path


def build_comparison_table(
    results: list[dict[str, Any]],
) -> Table:
    """Build Rich side-by-side comparison table per D-34.

    Args:
        results: List of per-model result dicts with keys:
        - "model": str
        - "book": str, "chapter": int
        - "wer": float
        - "mean_start_deviation": float
        - "mean_end_deviation": float
        - "avg_confidence": float
        - "cost_usd": float (0 for local models)
        - "time_sec": float
        - "aligned_verses": int
        - "total_verses": int

    Returns:
        Rich Table with columns for each metric, one row per model.
    """
    table = Table(title="Alignment Model Comparison")
    table.add_column("Model", justify="left")
    table.add_column("WER", justify="right")
    table.add_column("CER", justify="right")
    table.add_column("Start Dev (s)", justify="right")
    table.add_column("End Dev (s)", justify="right")
    table.add_column("Avg Conf", justify="right")
    table.add_column("Cost ($)", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("Verses", justify="right")

    for r in results:
        table.add_row(
            r["model"],
            f"{r['wer']:.3f}",
            f"{r.get('cer', 0.0):.3f}",
            f"{r['mean_start_deviation']:.2f}",
            f"{r['mean_end_deviation']:.2f}",
            f"{r['avg_confidence']:.1f}",
            f"{r['cost_usd']:.4f}",
            f"{r['time_sec']:.1f}",
            f"{r['aligned_verses']}/{r['total_verses']}",
        )

    return table


def save_evaluation_report(
    results: list[dict[str, Any]],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Save evaluation results as JSONL + summary JSON per D-30, D-31.

    Returns:
        Tuple of (jsonl_path, summary_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = output_dir / "evaluation.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary_path = output_dir / "evaluation_summary.json"
    summary = {
        "total_models": len(results),
        "results": results,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return jsonl_path, summary_path
