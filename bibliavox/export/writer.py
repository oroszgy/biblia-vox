"""JSONL export writer for alignment results.

Converts per-chapter evaluation matched JSON into standardized JSONL format
with full metadata (verse_ref, audio_file, timestamps, source, translation,
confidence, canonical_text, matched_text, wer, cer).

Uses mek.jsonl as canonical text source (D-17) and normalizes confidence
scores to 0-1 range via divide-by-max (D-15).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from bibliavox.align.evaluate import compute_cer, compute_wer

logger = logging.getLogger(__name__)

# Module-level cache for canonical text (lazy loaded)
_CANONICAL_TEXT: dict[tuple[str, int, str], str] | None = None


def load_canonical_text(data_dir: Path) -> dict[tuple[str, int, str], str]:
    """Load canonical text from mek.jsonl.

    Reads data_dir / "processed" / "text" / "mek.jsonl" line by line.
    Returns dict mapping (book, chapter_int, verse_str) -> text.
    Caches at module level with lazy loading.

    Args:
        data_dir: Root data directory (e.g., Path("data"))

    Returns:
        Dict mapping (book, chapter, verse) -> canonical text
    """
    global _CANONICAL_TEXT
    if _CANONICAL_TEXT is not None:
        return _CANONICAL_TEXT

    mek_path = data_dir / "processed" / "text" / "mek.jsonl"
    if not mek_path.exists():
        logger.warning("mek.jsonl not found at %s", mek_path)
        _CANONICAL_TEXT = {}
        return _CANONICAL_TEXT

    result: dict[tuple[str, int, str], str] = {}
    with open(mek_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                book = entry.get("book", "")
                chapter = int(entry.get("chapter", 0))
                verse = str(entry.get("verse", ""))
                text = entry.get("text", "")
                result[(book, chapter, verse)] = text
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Skipping malformed line in mek.jsonl: %s", e)

    _CANONICAL_TEXT = result
    return _CANONICAL_TEXT


def normalize_confidence(scores: list[float]) -> list[float]:
    """Normalize confidence scores to 0-1 range using divide-by-max (D-15).

    Args:
        scores: List of raw confidence scores

    Returns:
        List of normalized scores (0.0 to 1.0)
    """
    if not scores:
        return []

    max_score = max(scores)
    if max_score == 0:
        return [0.0] * len(scores)

    return [round(score / max_score, 4) for score in scores]


def export_chapter_jsonl(
    matched_path: Path,
    audio_file: str,
    translation: str,
    output_file: Path,
    data_dir: Path,
) -> int:
    """Export a single chapter's matched results to JSONL format (D-01 through D-07).

    Reads matched JSON, joins with canonical text from mek.jsonl, normalizes
    confidence, and writes flat JSONL rows with all D-07 fields.

    Args:
        matched_path: Path to *_matched.json file
        audio_file: Canonical audio file path (D-03)
        translation: Translation identifier (e.g., "SZIT")
        output_file: Output JSONL file path (append mode)
        data_dir: Root data directory for loading canonical text

    Returns:
        Number of lines written
    """
    try:
        with open(matched_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed matched JSON at {matched_path}: {e}") from e

    required_keys = ("model", "chapter", "verses")
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Matched JSON {matched_path} missing keys: {missing}")

    model = data["model"]
    chapter = data["chapter"]  # e.g., "TIT 1"
    parts = chapter.split()
    if len(parts) != 2:
        raise ValueError(
            f"Invalid chapter format in {matched_path}: {chapter!r}. Expected 'BOOK CHAPTER'."
        )
    book = parts[0]
    ch_num = int(parts[1])

    # Load canonical text
    canonical = load_canonical_text(data_dir)

    # Normalize confidence scores (D-15, D-16)
    verses = data["verses"]
    raw_scores = [v.get("confidence_score", 0) or 0.0 for v in verses]
    normalized_scores = normalize_confidence(raw_scores)

    lines_written = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for i, v in enumerate(verses):
            verse_id = v["verse_id"]

            # D-02: verse_ref format "BOOK CH:VS"
            verse_ref = f"{book} {ch_num}:{verse_id}"

            # D-04: canonical text from mek.jsonl, matched from alignment
            canonical_text = canonical.get((book, ch_num, verse_id), "")
            matched_text = v.get("matched_text", "")

            # D-05: per-verse WER/CER
            wer = compute_wer(canonical_text, matched_text) if canonical_text else 0.0
            cer = compute_cer(canonical_text, matched_text) if canonical_text else 0.0

            # D-06: null timestamps for failed alignments
            row = {
                "verse_ref": verse_ref,
                "audio_file": audio_file,
                "start_sec": v.get("start_sec"),  # None for failed
                "end_sec": v.get("end_sec"),  # None for failed
                "source": model,
                "translation": translation,
                "confidence": normalized_scores[i],
                "canonical_text": canonical_text,
                "matched_text": matched_text,
                "wer": round(wer, 4),
                "cer": round(cer, 4),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            lines_written += 1

    return lines_written


def is_chapter_complete(export_path: Path, model: str) -> bool:
    """Check if chapter export is complete per D-13.

    Complete = file exists AND all verses for the given model have non-null
    start_sec and end_sec.

    Args:
        export_path: Path to the JSONL export file
        model: Model ID to check

    Returns:
        True if chapter is complete, False otherwise
    """
    if not export_path.exists():
        return False

    found_any = False
    with open(export_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if row.get("source") != model:
                continue

            found_any = True
            if row.get("start_sec") is None or row.get("end_sec") is None:
                return False

    return found_any


def reset_canonical_text_cache() -> None:
    """Reset the module-level canonical text cache.

    Useful in tests that need to reload canonical text from different directories.
    """
    global _CANONICAL_TEXT
    _CANONICAL_TEXT = None
