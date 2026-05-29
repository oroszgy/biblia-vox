"""Verse marker detection and splitting for Bible text.

Detects embedded verse markers in JSONL verse text and either:
- Strips markers from Psalms superscriptions (target verse exists)
- Splits text at marker position (target verse missing)

Pattern types found in SZIT data:
- N) — most common, especially Psalms superscriptions
- ((N)) — 1Ki 22:52, 1Ch 12:40
- (N)N — 2Ki 11:6 (format: "(6)7")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Pattern priority: specific patterns first, general last
PATTERN_PN = re.compile(r"\((\d+)\)(\d)")  # (N)N — e.g., "(6)7" in 2Ki 11:6
PATTERN_DD = re.compile(r"\(\((\d+)\)\)")  # ((N)) — e.g., "((54))" in 1Ki 22:52
PATTERN_N = re.compile(r"\b(\d+)\)")  # N) — e.g., "2)" in Psalms

# Repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "processed" / "text"


@dataclass
class VerseMarker:
    """A detected verse marker in text."""

    pattern_type: str  # "(N)N", "((N))", or "N)"
    target_verse: int  # The verse number the marker points to
    position: int  # Character position in text
    raw_match: str  # The matched text


def detect_markers(text: str) -> list[VerseMarker]:
    """Detect all verse markers in text, sorted by position.

    Specific patterns ((N)) and (N)N take priority over general N).
    Overlapping markers are filtered — higher-priority patterns win.
    """
    # Collect all markers with priority (lower index = higher priority)
    # Each entry: (priority, pattern, ptype, target_group_index)
    all_markers: list[tuple[int, VerseMarker]] = []
    for priority, (pattern, ptype, target_group) in enumerate(
        [
            (PATTERN_PN, "(N)N", 2),  # target is digit AFTER paren: (6)7 → 7
            (PATTERN_DD, "((N))", 1),  # target is number inside: ((54)) → 54
            (PATTERN_N, "N)", 1),  # target is number before paren: 2) → 2
        ]
    ):
        for m in pattern.finditer(text):
            marker = VerseMarker(
                pattern_type=ptype,
                target_verse=int(m.group(target_group)),
                position=m.start(),
                raw_match=m.group(0),
            )
            all_markers.append((priority, marker))

    # Sort by position, then by priority (lower priority number wins)
    all_markers.sort(key=lambda x: (x[1].position, x[0]))

    # Filter out overlapping markers (higher-priority wins)
    result: list[VerseMarker] = []
    occupied: set[int] = set()
    for _priority, marker in all_markers:
        marker_range = set(
            range(marker.position, marker.position + len(marker.raw_match))
        )
        if marker_range & occupied:
            continue  # Overlaps with higher-priority marker
        occupied |= marker_range
        result.append(marker)

    return result


def fix_verses(
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, int]:
    """Fix verse markers in JSONL file.

    Reads szit.jsonl, detects markers, and either strips (Psalms) or splits.
    Returns: stats dict with counts of cleaned, split, and unchanged verses.
    """
    if input_path is None:
        input_path = _DEFAULT_OUTPUT_DIR / "szit.jsonl"
    if output_path is None:
        output_path = _DEFAULT_OUTPUT_DIR / "szit-fixed.jsonl"

    # Load all records into memory (grouped by book+chapter)
    chapters: dict[tuple[str, int], list[dict]] = {}
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            key = (record["book"], record["chapter"])
            chapters.setdefault(key, []).append(record)

    stats = {"cleaned": 0, "split": 0, "unchanged": 0}
    output_records = []

    for (book, chapter), verses in chapters.items():
        # Build set of existing verse numbers for this chapter
        existing_verses = {v["verse"] for v in verses}

        for verse_record in sorted(verses, key=lambda v: v["verse"]):
            text = verse_record["text"]
            markers = detect_markers(text)

            if not markers:
                output_records.append(verse_record)
                stats["unchanged"] += 1
                continue

            # Process each marker, tracking offset from prior strips
            current_text = text
            offset = 0
            split_occurred = False
            for marker in markers:
                adjusted_pos = marker.position + offset
                if marker.target_verse in existing_verses:
                    # Target verse exists — strip marker, update offset
                    current_text = (
                        current_text[:adjusted_pos]
                        + current_text[adjusted_pos + len(marker.raw_match) :]
                    )
                    offset -= len(marker.raw_match)
                    stats["cleaned"] += 1
                else:
                    # Target verse missing — split
                    before = current_text[:adjusted_pos].strip()
                    after = current_text[adjusted_pos + len(marker.raw_match) :].strip()

                    # Write "before" as current verse
                    output_records.append(
                        {
                            "book": book,
                            "chapter": chapter,
                            "verse": verse_record["verse"],
                            "text": before,
                        }
                    )
                    # Write "after" as new verse
                    output_records.append(
                        {
                            "book": book,
                            "chapter": chapter,
                            "verse": marker.target_verse,
                            "text": after,
                        }
                    )
                    existing_verses.add(marker.target_verse)
                    stats["split"] += 1
                    split_occurred = True
                    break

            if not split_occurred:
                # Cleanup-only: write the cleaned text
                verse_record["text"] = current_text.strip()
                output_records.append(verse_record)

    # Re-number verses sequentially within each chapter
    final_records = []
    chapter_groups: dict[tuple[str, int], list[dict]] = {}
    for record in output_records:
        key = (record["book"], record["chapter"])
        chapter_groups.setdefault(key, []).append(record)

    for (book, chapter), verses in chapter_groups.items():
        for i, verse_record in enumerate(sorted(verses, key=lambda v: v["verse"]), 1):
            verse_record["verse"] = i
            final_records.append(verse_record)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in final_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return stats
