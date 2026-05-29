---
phase: 03-audio-pipeline
plan: 02
subsystem: audio
tags: [ffmpeg, ffprobe, typer, taskfile, pytest]
requires:
  - phase: 03-audio-pipeline
    provides: playlist discovery, download command routing, canonical raw audio artifact layout
provides:
  - Deterministic MP3→WAV conversion with strict 16kHz mono PCM invariants
  - ffprobe-backed metadata normalization and deterministic CLI info output
  - Taskfile conversion and metadata inspection targets aligned to canonical paths
affects: [03-03, 04-transcription-alignment]
tech-stack:
  added: []
  patterns: [post-conversion probe assertions, required-binary fail-fast guidance, idempotent conversion task semantics]
key-files:
  created:
    - bibliavox/audio/convert.py
    - bibliavox/audio/metadata.py
    - tests/test_audio_convert.py
    - tests/test_audio_metadata.py
  modified:
    - bibliavox/cli/audio.py
    - bibliavox/audio/__init__.py
    - Taskfile.yml
    - tests/test_audio_cli.py
key-decisions:
  - "Conversion is accepted only after ffprobe confirms codec=pcm_s16le, sample_rate=16000, channels=1"
  - "audio info reports canonical raw chapter path and normalized measured values for auditable diagnostics"
  - "Taskfile conversion flow is idempotent by default with FORCE override for explicit reprocessing"
patterns-established:
  - "audio convert enforces ffmpeg availability and surfaces setup guidance as hard failure"
  - "audio info enforces ffprobe availability and reports deterministic key-value output"
requirements-completed: [AUD-03, AUD-04]
duration: 4 min
completed: 2026-05-29
---

# Phase 3 Plan 02: MP3→WAV conversion + ffprobe metadata CLI Summary

**Strict ffmpeg conversion plus ffprobe-based metadata diagnostics now enforce alignment-safe WAV artifacts and traceable chapter audio inspection.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-29T20:50:41Z
- **Completed:** 2026-05-29T20:54:24Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Implemented `convert_to_wav` with deterministic ffmpeg flags (`-ac 1 -ar 16000 -c:a pcm_s16le`), timeout bounds, missing-binary guidance, and post-conversion invariant validation.
- Implemented `probe_audio` / `format_audio_info` for normalized ffprobe metadata and added `bibliavox audio convert` + `bibliavox audio info` CLI commands using canonical chapter paths.
- Added `audio:convert`, `audio:convert-all`, and `audio:info` Taskfile targets plus package exports for conversion and metadata helpers.

## task Commits

Each task was committed atomically:

1. **task 1: implement ffmpeg conversion with strict WAV invariants**
   - `26d98ca` (test): RED tests for ffmpeg flags, failure handling, and invariant rejection
   - `b5d72d8` (feat): conversion implementation with timeout, invariant checks, and typed errors
2. **task 2: implement ffprobe metadata extractor and CLI info rendering**
   - `463ad1e` (test): RED tests for metadata normalization and CLI info error handling
   - `d86cbdc` (feat): metadata module and CLI convert/info command integration
3. **task 3: wire conversion Taskfile targets and run smoke checks**
   - `ef895e5` (feat): Taskfile conversion/info targets and audio package exports

## Files Created/Modified
- `bibliavox/audio/convert.py` - MP3→WAV conversion orchestration with strict invariant enforcement and explicit ffmpeg setup guidance.
- `bibliavox/audio/metadata.py` - ffprobe execution, normalized metadata extraction, and deterministic info formatting.
- `bibliavox/cli/audio.py` - adds `audio convert` and `audio info` commands bound to canonical raw/prepared paths.
- `Taskfile.yml` - introduces `audio:convert`, `audio:convert-all`, and `audio:info` targets with idempotent defaults and force override behavior.
- `bibliavox/audio/__init__.py` - exports conversion and metadata helpers for package consumers.
- `tests/test_audio_convert.py` - conversion command contract and invariant assertion tests.
- `tests/test_audio_metadata.py` - ffprobe normalization and CLI info behavior tests.
- `tests/test_audio_cli.py` - compatibility fix for explicit `download` subcommand invocation.

## Decisions Made
- Enforced threat-model mitigation T-03-05 by rejecting converted WAV artifacts unless ffprobe confirms exact codec/sample-rate/channel invariants.
- Enforced threat-model mitigation T-03-06 by adding subprocess timeout bounds to ffmpeg/ffprobe invocations.
- Enforced threat-model mitigation T-03-08 by including canonical chapter file paths in metadata output.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing CLI tests after adding new audio subcommands**
- **Found during:** task 2 (CLI command extension)
- **Issue:** Existing `tests/test_audio_cli.py` invoked the app root without the `download` subcommand and began failing once multiple subcommands existed.
- **Fix:** Updated invocations to call `audio download ...` explicitly in all existing tests.
- **Files modified:** `tests/test_audio_cli.py`
- **Verification:** `uv run pytest tests/test_audio_cli.py -x -v`
- **Committed in:** `46b6769`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** No scope creep; fix was directly required by current task changes to keep existing CLI behavior covered.

## Issues Encountered
- `rg` is unavailable in this environment; equivalent acceptance checks were completed with repository grep tooling and direct verification commands.
- `gsd-sdk` state query handlers were unavailable in this environment; planning docs were updated directly for continuity.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 plan 02 now guarantees deterministic prepared WAV artifacts and deterministic chapter metadata inspection outputs for downstream seek/index workflows.
- Phase 3 plan 03 can consume `data/prepared/audio/{USX}/{chapter:03d}.wav` with confidence that conversion invariants are enforced.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-audio-pipeline/03-02-SUMMARY.md`
- FOUND: `26d98ca`
- FOUND: `b5d72d8`
- FOUND: `463ad1e`
- FOUND: `d86cbdc`
- FOUND: `ef895e5`
- FOUND: `46b6769`

---
*Phase: 03-audio-pipeline*
*Completed: 2026-05-29*
