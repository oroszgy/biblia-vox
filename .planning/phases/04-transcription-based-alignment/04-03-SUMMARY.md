---
phase: 04-transcription-based-alignment
plan: 3
subsystem: alignment-matching
tags:
  - matching
  - rapidfuzz
  - cli
dependency_graph:
  requires:
    - ALN-02
  provides:
    - align match command
    - Verse-level timestamps with confidence scores
  affects:
    - Final pipeline export
tech_stack:
  added:
    - rapidfuzz
  patterns:
    - Fuzzy sequence matching
    - Sliding window word mapping
key_files:
  created:
    - bibliavox/align/match.py
  modified:
    - bibliavox/cli/align.py
decisions:
  - "Used RapidFuzz `partial_ratio_alignment` on the full sequence of transcribed words joined as a single string to find the optimal contiguous match for each verse."
  - "Maintained exact character-to-word index mappings to accurately translate the `dest_start` and `dest_end` from the fuzz matcher back into word timestamps."
metrics:
  duration: 10m
  tasks_completed: 2
  files_changed: 2
  commits: 1
---

# Phase 04 Plan 3: Fuzzy Matching and CLI Summary

Implemented fuzzy matching using RapidFuzz to align intermediate transcribed words against the canonical SZIT Bible texts, outputting verse-level timestamps.

## Execution Details

1. **Fuzzy Matching Logic**: Created `bibliavox/align/match.py`. Implemented a sliding window/partial alignment approach where the sequence of transcribed words is mapped against the canonical verse text. Exact character bounds from RapidFuzz's `partial_ratio_alignment` are translated back to word array indices, extracting the exact start and end timestamps.
2. **Typer CLI**: Updated `bibliavox/cli/align.py` to add the `match` command. It reads the specific book and chapter from `data/processed/text/szit.jsonl`, compares it against the generated transcript JSON, and writes out the final verse timestamp mappings to `data/processed/align/`.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
- `bibliavox/align/match.py` created and tested successfully.
- `bibliavox/cli/align.py` updated with the `match` command.
- Commit exists: 250a9d0
