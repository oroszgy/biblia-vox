# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-28)

**Core value:** Every verse of the Szent István Társulat Bible can be located in its audio recording — with precise timestamps and confidence metadata.
**Current focus:** Phase 2 — Text Acquisition & Validation

## Current Position

Phase: 2 of 8 (Text Acquisition & Validation)
Plan: 0 of ? in current phase
Status: Context gathered
Last activity: 2026-05-29 — Phase 2 context gathered (SZIT JSON as primary source)

Progress: [██░░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 8 min
- Total execution time: 0.34 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2/2 | 13 min | 6.5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (10 min), 01-02 (3 min)
- Trend: Improving (faster on second plan)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 8-phase structure; Docker absorbed into alignment phases, CLI/Taskfile distributed across all phases
- [Roadmap]: Phases 2/3 are parallelizable after Phase 1; Phase 4 is the convergence point
- [Roadmap]: Docker infrastructure built incrementally when Phase 4 needs GPU models
- [Roadmap]: Each phase delivers working Typer commands and Taskfile targets
- [01-01]: Used frozen dataclasses (Book, BookSchema) for immutable reference data
- [01-01]: Module-level caches (_BOOKS, _SCHEMAS) with lazy loading on first access
- [01-01]: Catholic Vulgate ordering for books (Daniel/Esther after minor prophets)
- [01-01]: Empty szentiras_api_key default — requires manual setup for Phase 2
- [01-02]: Entry point changed from bibliavox.cli:app to bibliavox.main:main
- [01-02]: CLI follows Pattern 4 (Typer Sub-Command Groups) from ARCHITECTURE.md
- [01-02]: Taskfile uses go-task (task command not available, go-task is)
- [02]: szentiras.eu API dropped — not viable without API key
- [02]: Primary text source is peterpolgar/Biblia-json-xml (H_Kaldi_SZIT.json, Unlicense)
- [02]: mek.oszk.hu HTML parser deferred — SZIT JSON is sole source for v1
- [02]: Two-stage normalization: lightweight (NFC, whitespace) then schema matching
- [02]: Reproducible pipeline: all steps in Taskfile, data in data/raw/ and data/processed/
- [02]: Verse count validation against versification schema, JSON discrepancy reports

### Pending Todos

None yet.

### Blockers/Concerns

- ~~szentiras.eu API key requires emailing maintainers~~ → Resolved: switched to peterpolgar/Biblia-json-xml (Unlicense)
- mek.oszk.hu audio completeness for all 73 Catholic books unverified (affects Phase 3)
- Hungarian Whisper LoRA performance on Bible narration (literary register) unverified (affects Phase 4)

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-29
Stopped at: Phase 2 context gathered
Resume file: .planning/phases/02-text-acquisition/02-CONTEXT.md
