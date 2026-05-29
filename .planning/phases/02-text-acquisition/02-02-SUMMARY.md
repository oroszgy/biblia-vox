---
phase: 02-text-acquisition
plan: 02
subsystem: text
tags: [normalization, validation, nfc, discrepancy-report]
dependency_graph:
  requires: [02-01]
  provides: [normalizer, validator]
  affects: [03-audio-pipeline]
tech_stack:
  added: []
  patterns: [frozen-dataclasses, enum-severity, json-reporting]
key_files:
  created:
    - bibliavox/text/normalizer.py
    - bibliavox/text/validator.py
    - tests/test_text_normalizer.py
    - tests/test_text_validator.py
  modified:
    - bibliavox/cli/text.py
    - bibliavox/text/__init__.py
decisions:
  - "Two-stage normalization: Stage 1 (NFC, whitespace, line endings) in normalizer.py, Stage 2 (schema matching) in validator.py"
  - "Severity enum with ERROR/WARNING/INFO levels for discrepancy classification"
  - "JSON discrepancy reports for machine-readable validation output"
metrics:
  duration: 10 min
  completed: 2026-05-29T12:25:00Z
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 2 Plan 02: Normalization Pipeline & Validation Summary

**One-liner:** NFC normalization pipeline with whitespace collapse, verse count validation against versification schema, and JSON discrepancy reporting

## What Was Built

### Normalization Module (`bibliavox/text/normalizer.py`)
- `normalize_text()` — Stage 1 lightweight normalization:
  - NFC Unicode normalization (composed form)
  - Line ending standardization (\r\n → \n)
  - Whitespace collapse (multiple spaces → single space)
  - Strip leading/trailing whitespace
- `normalize_verse()` — Normalize a single verse text
- `normalize_chapter()` — Normalize all verses in a chapter

### Validator Module (`bibliavox/text/validator.py`)
- `validate_chapter()` — Validate a chapter's verses against versification schema
  - Verse count matching
  - Empty verse text detection
  - Missing book/chapter detection
- `validate_book()` — Validate all chapters in a book
- `generate_report()` — Generate JSON discrepancy report
- `Discrepancy` dataclass — Structured discrepancy record
- `Severity` enum — ERROR, WARNING, INFO levels

### CLI Commands (`bibliavox/cli/text.py`)
- `bibliavox text validate --book <id> [--chapter <n>]` — Validate verse counts
- `bibliavox text normalize --book <id> | --all` — Normalize Bible text
- Rich table output for validation results
- JSON report output for machine consumption

## TDD Gate Compliance

- **RED gate:** test(02-02): add failing tests for text normalization pipeline (4c77f56)
- **GREEN gate:** feat(02-02): implement text normalization pipeline (707080a)
- **RED gate:** test(02-02): add failing tests for verse count validation (2d926fc)
- **GREEN gate:** feat(02-02): implement verse count validation and JSON reporting (3be82a4)
- **GREEN gate:** feat(02-02): add validate and normalize CLI commands (df00f05)

## Verification

1. ✅ All 52 tests pass: `uv run pytest tests/test_text_source.py tests/test_text_mapping.py tests/test_text_normalizer.py tests/test_text_validator.py tests/test_cli_text.py -x -v`
2. ✅ CLI works: `uv run bibliavox text --help` shows all 4 commands
3. ✅ Normalization: NFC, whitespace collapse, line ending standardization
4. ✅ Validation: Verse count comparison, JSON discrepancy reports

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

No stubs remain. All planned functionality is implemented.

## Threat Flags

No new security-relevant surface introduced. Validation reports contain only Bible text metadata, no PII.
