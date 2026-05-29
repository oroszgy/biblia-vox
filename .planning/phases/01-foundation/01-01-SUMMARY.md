---
phase: 01-foundation
plan: 01
subsystem: reference
tags: [pydantic-settings, json, catholic-bible, hungarian, versification, usx]

# Dependency graph
requires: []
provides:
  - "73-book Catholic Bible catalog with Hungarian names, abbreviations, USX codes"
  - "Versification schema with chapter/verse counts per book"
  - "Pydantic Settings configuration with .env support"
  - "Static JSON reference data at data/reference/"
  - "Generation script for reproducible JSON from szentiras.eu source"
affects: [text, audio, align, export, cli]

# Tech tracking
tech-stack:
  added: [pydantic-settings, typer, rich, httpx]
  patterns: [json-load-at-import, singleton-settings, dataclass-frozen]

key-files:
  created:
    - bibliavox/__init__.py
    - bibliavox/config.py
    - bibliavox/reference/__init__.py
    - bibliavox/reference/books.py
    - bibliavox/reference/schema.py
    - data/reference/books.json
    - data/reference/versification.json
    - scripts/generate_reference.py
    - tests/__init__.py
    - tests/test_reference.py
    - tests/test_config.py
    - .gitignore
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "Used frozen dataclasses (Book, BookSchema) for immutable reference data"
  - "Module-level _BOOKS/_SCHEMAS caches with lazy loading on first access"
  - "Path resolution: 3 levels up from bibliavox/reference/ to repo root"
  - "Catholic Vulgate ordering for books (Daniel/Esther after minor prophets)"

patterns-established:
  - "JSON-at-import: static JSON loaded once at module import, cached in module global"
  - "Frozen dataclass: reference data types are immutable (frozen=True, slots=True)"
  - "Singleton settings: get_settings() returns cached instance, reset_settings() for tests"
  - "BIBLIAVOX_ prefix: all environment variables use consistent prefix"

requirements-completed: [TEXT-04, TEXT-06, INF-02]

# Metrics
duration: 10min
completed: 2026-05-29
---

# Phase 1 Plan 01: Reference Data & Configuration Summary

**73-book Catholic Bible catalog with Hungarian names/abbreviations/USX codes, versification schema with chapter/verse counts, and Pydantic Settings configuration with .env support**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-29T10:39:55Z
- **Completed:** 2026-05-29T10:50:51Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Complete 73-book Catholic Bible catalog (46 OT + 27 NT) with Hungarian names, abbreviations, USX codes, book numbers, testament classification, and deuterocanonical flags
- Versification schema with accurate chapter/verse counts for all 73 books (including Catholic additions to Daniel and Esther)
- Pydantic Settings configuration with BIBLIAVOX_ prefix, .env support, and sensible defaults
- Static JSON reference data at data/reference/ (no runtime network dependency)
- Generation script (scripts/generate_reference.py) for reproducible JSON from szentiras.eu tdverse source
- 26 passing tests (20 reference + 6 config)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project structure and reference data module** - `4900bda` (feat)
2. **Task 2: Create Pydantic Settings configuration module** - `f7a88a1` (feat)

## Files Created/Modified

- `bibliavox/__init__.py` - Package init with version
- `bibliavox/config.py` - Pydantic Settings with BIBLIAVOX_ prefix, singleton pattern
- `bibliavox/reference/__init__.py` - Re-exports for reference module
- `bibliavox/reference/books.py` - Book catalog: load_books, lookup_by_abbreviation, lookup_by_usx_code
- `bibliavox/reference/schema.py` - Versification: load_versification, get_chapter_count, get_verse_count
- `data/reference/books.json` - Static JSON: 73 books with Hungarian metadata
- `data/reference/versification.json` - Static JSON: chapter/verse counts per book
- `scripts/generate_reference.py` - CLI script to regenerate JSON from szentiras.eu source
- `tests/test_reference.py` - 20 tests covering books and versification
- `tests/test_config.py` - 6 tests covering settings, env override, singleton
- `pyproject.toml` - Updated with dependencies (typer, rich, pydantic-settings, httpx)
- `.gitignore` - Python, .env, data directories (keeps data/reference/)
- `uv.lock` - Updated lock file

## Decisions Made

- Used frozen dataclasses (Book, BookSchema) for immutable reference data — type-safe, hashable, no mutation bugs
- Module-level caches (_BOOKS, _SCHEMAS) with lazy loading — single JSON read per module lifetime
- Path resolution: 3 levels up from bibliavox/reference/ to repo root — works regardless of cwd
- Catholic Vulgate ordering for books (Daniel and Esther placed after minor prophets with deuterocanonical additions)
- Empty szentiras_api_key default — requires manual setup (known blocker)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. (szentiras_api_key defaults to empty; will be needed for Phase 2.)

## Next Phase Readiness

- Reference data module complete and tested — ready for text/acoustic pipeline phases
- Configuration loads from .env with sensible defaults — ready for CLI integration (Plan 01-02)
- Static JSON data committed — no runtime network dependency for reference lookups
- Remaining Phase 1 plan: 01-02-PLAN.md (CLI scaffolding & Taskfile)

---

*Phase: 01-foundation*
*Completed: 2026-05-29*

## Self-Check: PASSED

All 12 created files verified on disk. Both task commits (4900bda, f7a88a1) verified in git log.
