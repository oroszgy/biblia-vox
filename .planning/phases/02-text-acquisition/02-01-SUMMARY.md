---
phase: 02-text-acquisition
plan: 01
subsystem: text
tags: [text, source, mapping, cli, szit]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [text-source, book-mapping]
  affects: [02-02]
tech_stack:
  added: []
  patterns: [module-level-caching, frozen-dataclasses, typer-subcommand-groups]
key_files:
  created:
    - bibliavox/text/__init__.py
    - bibliavox/text/source.py
    - bibliavox/text/mapping.py
    - bibliavox/cli/text.py
    - tests/test_text_source.py
    - tests/test_text_mapping.py
    - tests/test_cli_text.py
  modified:
    - bibliavox/main.py
    - Taskfile.yml
decisions:
  - "Direct English→USX mapping (73 books) instead of Hungarian abbreviation intermediary"
  - "SZIT JSON uses Python literal format (single quotes), not standard JSON — need ast.literal_eval for manual inspection but json.load works for the actual file"
  - "Deuterocanonical books (7) are NOT in the SZIT JSON source — only 66 books available"
metrics:
  duration: 8 min
  completed: 2026-05-29T12:15:00Z
  tasks_completed: 2
  files_created: 7
  files_modified: 2
---

# Phase 2 Plan 01: SZIT Text Source & Book Mapping Summary

**One-liner:** SZIT Bible JSON loading with English→USX book mapping for 73 Catholic books, CLI fetch/info commands, and Taskfile download targets

## What Was Built

### Text Source Module (`bibliavox/text/source.py`)
- `load_szit_json()` — Loads H_Kaldi_SZIT.json from data/raw/text/ with module-level caching
- `get_chapter_verses()` — Extracts verses for a book/chapter as {int: str} dict
- `get_verse_text()` — Gets specific verse text by book/chapter/verse

### Book Mapping Module (`bibliavox/text/mapping.py`)
- `load_book_mapping()` — Returns {english_name: usx_code} for all 73 Catholic books
- `english_to_usx()` — Looks up USX code by English book name
- Direct mapping approach (English→USX) instead of Hungarian abbreviation intermediary
- Handles 66 standard books + 7 deuterocanonical books

### CLI Commands (`bibliavox/cli/text.py`)
- `bibliavox text fetch --book <id> [--chapter <n>]` — Fetch and display Bible text
- `bibliavox text info <book_id>` — Show book info with chapter/verse counts
- Follows Pattern 4 (Typer Sub-Command Groups) from reference.py

### Taskfile Targets
- `text:fetch` — Download SZIT JSON from GitHub (idempotent)
- `text:test` — Test text fetch with sample chapter
- `text:normalize` — Normalize all Bible text (placeholder for Plan 02-02)
- `text:validate` — Validate verse counts (placeholder for Plan 02-02)

## Key Findings

1. **SZIT JSON format:** Uses Python literal format (single quotes), not standard JSON. However, `json.load()` works fine for the actual file.
2. **Book count:** The SZIT JSON contains only 66 books (Protestant canon). The 7 deuterocanonical books are NOT in this source.
3. **Mapping approach:** Built direct English→USX mapping instead of going through Hungarian abbreviations, because books.json uses different abbreviations than the mapping file.

## TDD Gate Compliance

- **RED gate:** test(02-01): add failing tests for SZIT text source and book mapping (c515774)
- **GREEN gate:** feat(02-01): implement SZIT text source and book mapping (afe28bf)
- **GREEN gate:** feat(02-01): implement text CLI and Taskfile targets (7767402)

## Verification

1. ✅ All 26 tests pass: `uv run pytest tests/test_text_source.py tests/test_text_mapping.py tests/test_cli_text.py -x -v`
2. ✅ CLI works: `uv run bibliavox text --help` shows fetch and info commands
3. ✅ Book mapping: 73 books mapped (66 standard + 7 deuterocanonical)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cache invalidation in test_raises_on_missing_file**
- **Found during:** Task 1 RED phase
- **Issue:** Test didn't clear module-level cache before testing missing file
- **Fix:** Added cache clearing before the assertion
- **Files modified:** tests/test_text_source.py
- **Commit:** c515774

**2. [Rule 1 - Bug] Fixed Hungarian abbreviation mismatch in mapping**
- **Found during:** Task 1 GREEN phase
- **Issue:** Hungarian abbreviations in books.json differ from mapping file (e.g., "Ter" vs "1Móz" for Genesis)
- **Fix:** Used direct English→USX mapping instead of Hungarian abbreviation intermediary
- **Files modified:** bibliavox/text/mapping.py
- **Commit:** afe28bf

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| text:normalize task | Taskfile.yml | — | Placeholder for Plan 02-02 implementation |
| text:validate task | Taskfile.yml | — | Placeholder for Plan 02-02 implementation |

## Threat Flags

No new security-relevant surface introduced. Bible text is public domain, no PII involved.
