---
phase: 03-audio-pipeline
plan: 04
subsystem: audio
tags: [taskfile, typer, rich-progress, downloader, gap-closure]
requires:
  - phase: 03-audio-pipeline
    provides: playlist discovery, resilient downloader, conversion/prepare/seek command suite
provides:
  - Batch download callback instrumentation with live progress updates during execution
  - Executable Taskfile command contract aligned to go-task variable syntax in roadmap truths
  - Regression tests that lock callback, progress signaling, and failure-exit semantics
affects: [03-VERIFICATION, 04-transcription-alignment]
tech-stack:
  added: []
  patterns: [callback-driven progress accounting, deterministic batch summary after progress UI, go-task variable-first command contract]
key-files:
  created: []
  modified:
    - bibliavox/audio/downloader.py
    - bibliavox/cli/audio.py
    - tests/test_audio_downloader.py
    - tests/test_audio_cli.py
    - Taskfile.yml
    - .planning/ROADMAP.md
key-decisions:
  - "Batch progress is driven by a per-result callback (`on_result`) from downloader to CLI so summary accounting stays deterministic under concurrency"
  - "Phase 3 acceptance commands are standardized on go-task variable syntax (BOOK/CHAPTER/WORKERS) because task-level flag parsing is not supported"
patterns-established:
  - "`audio download --all` now emits visible in-run progress signaling, then always prints final downloaded/skipped/failed counts"
  - "Taskfile command docs and roadmap truths must mirror executable go-task invocations"
requirements-completed: [AUD-01, AUD-02, AUD-03]
duration: 2 min
completed: 2026-05-30
---

# Phase 3 Plan 04: Gap-closure command contract + batch progress Summary

**Batch audio downloads now expose live progress while running, and Phase 3 roadmap commands are updated to executable go-task variable syntax.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-30T04:46:00Z
- **Completed:** 2026-05-30T04:47:54Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added `on_result` callback support in `download_all` and wired Rich progress columns in batch CLI download flow.
- Preserved deterministic end-of-run accounting (`downloaded/skipped/failed`) and non-zero exit behavior when failures occur.
- Aligned Phase 3 ROADMAP command truths to executable go-task variable forms and added Taskfile defaults/documentation for worker and required vars.

## task Commits

Each task was committed atomically:

1. **task 1: add batch progress instrumentation to download workflow**
   - `30a07d8` (test): RED coverage for callback invocation, progress output signaling, and batch failure exit semantics
   - `bd9043b` (feat): downloader callback hook and CLI live progress wiring for `audio download --all`
2. **task 2: standardize executable Taskfile command contract for verification commands**
   - `9cb41b7` (docs): roadmap truth commands switched to go-task vars; Taskfile worker default + invocation contract note

## Files Created/Modified
- `bibliavox/audio/downloader.py` - adds optional `on_result` callback executed once per manifest entry.
- `bibliavox/cli/audio.py` - adds batch progress instrumentation (spinner/progress/count columns) with callback-driven updates.
- `tests/test_audio_downloader.py` - adds callback invocation regression for `download_all`.
- `tests/test_audio_cli.py` - extends batch tests for callback wiring, visible progress signaling, and non-zero failure exit.
- `Taskfile.yml` - sets default `WORKERS=4`, clarifies required BOOK/CHAPTER vars, and documents go-task parser behavior.
- `.planning/ROADMAP.md` - updates Phase 3 success criteria commands to executable task variable syntax.

## Decisions Made
- Used callback-based progress updates instead of polling to keep concurrency-safe state updates tightly coupled to chapter completion events.
- Kept deterministic final summary output as the canonical success/failure artifact even when live progress is enabled.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `gsd-sdk` CLI was unavailable in this execution environment (`command not found`), so planning artifact updates were applied directly in markdown files.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 verification gaps for task command contract and batch-progress observability are closed.
- Re-verification can now execute documented Phase 3 task commands verbatim (using go-task vars) and observe in-run batch feedback.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-audio-pipeline/03-04-SUMMARY.md`
- FOUND: `30a07d8`
- FOUND: `bd9043b`
- FOUND: `9cb41b7`
