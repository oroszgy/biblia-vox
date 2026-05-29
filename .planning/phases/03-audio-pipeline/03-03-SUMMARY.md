---
phase: 03-audio-pipeline
plan: 03
subsystem: audio
tags: [wav, seek-index, typer, taskfile, pytest]
requires:
  - phase: 03-audio-pipeline
    provides: strict WAV conversion invariants, ffprobe metadata extraction, audio convert/info CLI
provides:
  - Sample-accurate WAV seek index sidecars for prepared chapters
  - Chapter prepare orchestration producing wav/meta/index artifacts with idempotent rerun semantics
  - CLI and Taskfile seek preview workflows that resolve windows from WAV samples (not MP3 timebase)
affects: [04-transcription-alignment, 05-forced-alignment]
tech-stack:
  added: []
  patterns: [sample-based seek windows, index schema validation before seek, constrained preview output paths]
key-files:
  created:
    - bibliavox/audio/seek_index.py
    - bibliavox/audio/pipeline.py
    - tests/test_audio_seek_index.py
    - tests/test_audio_pipeline.py
  modified:
    - bibliavox/cli/audio.py
    - bibliavox/audio/__init__.py
    - bibliavox/audio/convert.py
    - Taskfile.yml
    - tests/test_audio_cli.py
key-decisions:
  - "Seek index schema is persisted as JSON sidecar with sample_rate, total_samples, duration_sec, wav_path, book_usx, chapter, created_at"
  - "audio seek resolves preview windows from index sample offsets and writes deterministic seek reports for reproducible verification"
  - "Absolute seek output paths are restricted to prepared-root or /tmp to mitigate filesystem escape risk"
patterns-established:
  - "prepare_chapter orchestrates convert -> probe -> meta write -> index write under canonical prepared paths"
  - "Taskfile prepare/seek targets expose idempotent defaults with explicit FORCE override behavior"
requirements-completed: [AUD-05]
duration: 6 min
completed: 2026-05-29
---

# Phase 3 Plan 03: Seek index + prepare/seek workflows Summary

**WAV sample-index sidecars plus prepare/seek CLI workflows now provide deterministic timestamp preview extraction without MP3 timebase drift.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-29T20:58:57Z
- **Completed:** 2026-05-29T21:04:52Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Implemented `build_seek_index`, `resolve_sample_window`, and `write_seek_preview` for deterministic, sample-accurate WAV indexing and preview extraction.
- Implemented `prepare_chapter` orchestration and added `audio prepare` / `audio seek` commands that consume prepared WAV/index sidecars under canonical paths.
- Added Taskfile `audio:prepare`, `audio:prepare-all`, and `audio:seek` targets and verified end-to-end CLI/task smoke flows for AUD-05.

## task Commits

Each task was committed atomically:

1. **task 1: implement sample-accurate seek index and preview primitives**
   - `e7b20b5` (feat): seek index module and tests for schema, window clamping, and WAV preview slicing
2. **task 2: implement prepare orchestration and CLI seek/prepare commands**
   - `acc9d35` (feat): prepare pipeline, CLI commands, API exports, and integration tests
3. **task 3: wire Taskfile seek/prepare targets and run end-to-end smoke checks**
   - `ecf4a3d` (feat): Taskfile prepare/seek targets and force/idempotent argument wiring

Additional task-scoped hardening commit:
- `a578dfc` (fix): enforce seek output path restriction and prepare force propagation with regression tests

## Files Created/Modified
- `bibliavox/audio/seek_index.py` - seek index JSON sidecar builder, sample-window resolver, and WAV preview writer.
- `bibliavox/audio/pipeline.py` - chapter preparation orchestration producing `.wav`, `.meta.json`, and `.index.json` artifacts.
- `bibliavox/cli/audio.py` - adds `prepare` and `seek` commands with index validation, deterministic seek report output, and path safety guard.
- `Taskfile.yml` - adds `audio:prepare`, `audio:prepare-all`, and `audio:seek` workflows.
- `bibliavox/audio/__init__.py` - exports pipeline and seek-index APIs.
- `bibliavox/audio/convert.py` - adds idempotent `force` contract needed by prepare orchestration.
- `tests/test_audio_seek_index.py` - unit coverage for index generation and preview extraction.
- `tests/test_audio_pipeline.py` - orchestration tests for prepare success, skip, and force reprocess behavior.
- `tests/test_audio_cli.py` - CLI tests for prepare/seek behavior and seek output path restriction.

## Decisions Made
- Implemented AUD-05 with sample-based indexing against prepared WAV artifacts only, avoiding MP3 timestamp math in the seek path.
- Enforced threat mitigation T-03-09 by validating required seek index fields before resolving sample windows.
- Enforced threat mitigation T-03-11 by constraining absolute preview output paths to project-prepared roots or `/tmp`.
- Enforced threat mitigation T-03-12 by emitting deterministic seek reports (`source_wav`, `start_sample`, `end_sample`, `output`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `--force` did not propagate through prepare conversion path**
- **Found during:** task 2 verification
- **Issue:** `prepare_chapter(..., force=True)` re-entered orchestration but conversion helper still defaulted to `force=False`, violating explicit reprocess semantics.
- **Fix:** Forwarded force flag from pipeline to conversion and added regression test for forced reprocessing.
- **Files modified:** `bibliavox/audio/pipeline.py`, `tests/test_audio_pipeline.py`
- **Verification:** `uv run pytest tests/test_audio_pipeline.py tests/test_audio_cli.py tests/test_audio_seek_index.py -x -v`
- **Committed in:** `a578dfc`

**2. [Rule 2 - Missing Critical] Added seek output path guard for filesystem boundary safety**
- **Found during:** task 2 threat-model review (T-03-11)
- **Issue:** `audio seek --output` previously allowed unrestricted absolute paths, enabling writes outside expected audio roots.
- **Fix:** Added output-path validation that allows relative paths, prepared-root absolute paths, and `/tmp` absolute paths; rejects other absolute destinations.
- **Files modified:** `bibliavox/cli/audio.py`, `tests/test_audio_cli.py`
- **Verification:** `uv run pytest tests/test_audio_pipeline.py tests/test_audio_cli.py tests/test_audio_seek_index.py -x -v`
- **Committed in:** `a578dfc`

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug, 1 Rule 2 critical missing mitigation)
**Impact on plan:** Both fixes were correctness/security requirements directly tied to AUD-05 and plan threat mitigations; no scope creep.

## Issues Encountered
- `gsd-sdk` CLI/state handlers were unavailable in this execution environment (`command not found`), so planning artifacts were updated directly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 audio pipeline is now complete for AUD-01..AUD-05 with canonical raw/prepared artifact flows and sample-accurate seek preview verification.
- Phase 4 can consume prepared WAV and seek index sidecars directly for alignment-stage timestamp operations.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-audio-pipeline/03-03-SUMMARY.md`
- FOUND: `e7b20b5`
- FOUND: `acc9d35`
- FOUND: `ecf4a3d`
- FOUND: `a578dfc`
