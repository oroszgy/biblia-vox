---
phase: 05-forced-alignment-and-alternatives
plan: 1
subsystem: alignment
tags: [torchaudio, mms-fa, forced-alignment, ctc, gauntlet]

# Dependency graph
requires:
  - phase: 04-transcription-based-alignment
    provides: Docker GPU alignment infrastructure, model gauntlet setup, faster-whisper pipeline
  - phase: 03-audio-pipeline
    provides: Prepared WAV audio files at data/prepared/audio/{USX}/
provides:
  - MMS_FA forced alignment pipeline with phone-level and word-level output
  - Corrected model gauntlet (4 models, no hubert text BERT)
  - align forced CLI command and Taskfile targets
  - Updated Docker config for torchaudio MMS_FA
affects: [06-calibration-and-alignment-comparison, export]

# Tech tracking
tech-stack:
  added: [torchaudio MMS_FA, mms-fa model type, ctc model type]
  patterns: [CTC forced alignment, character-to-word span grouping, phone-level output]

key-files:
  created:
    - "bibliavox/align/forced.py"
    - "tests/test_forced.py"
  modified:
    - "bibliavox/config.py"
    - "docker/Dockerfile.align"
    - "bibliavox/cli/align.py"
    - "Taskfile.yml"

key-decisions:
  - "Replaced hubert-base-cc-hu (text BERT) with mms-1b-fl102 and wav2vec2-large-xlsr-53-hungarian in gauntlet"
  - "MMS_FA uses with_star=True for robust alignment with transcript mismatches"
  - "Character spans grouped into words using transcript word boundaries (no word-boundary token in MMS_FA)"
  - "Standalone MMS_FA pipeline (not hybrid with RapidFuzz) per D-06 discretion"

patterns-established:
  - "Phone-level and verse-level dual output for forced alignment (D-02, D-05)"
  - "Results saved to data/aligned/mms_fa/{USX}/{chapter}.json and _phones.json"

requirements-completed: [ALN-03]

# Metrics
duration: 7min
completed: 2026-06-02
---

# Phase 5 Plan 1: MMS_FA Forced Alignment Summary

**MMS_FA CTC forced alignment pipeline with phone-level and word-level timestamps, corrected 4-model gauntlet, and `align forced` CLI command**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-02T12:03:51Z
- **Completed:** 2026-06-02T12:10:36Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Corrected model gauntlet: replaced hubert-base-cc-hu (text BERT) with facebook/mms-1b-fl102 and sarpba/wav2vec2-large-xlsr-53-hungarian
- Implemented MMS_FA forced alignment pipeline using torchaudio.pipelines.MMS_FA bundle (model + tokenizer + aligner)
- Character-to-word span grouping algorithm for MMS_FA (no word-boundary token)
- `align forced` CLI command with Rich table output and phone-level summary
- Taskfile targets for single-chapter and batch forced alignment via Docker

## Task Commits

Each task was committed atomically:

1. **task 1: update gauntlet config and Docker for MMS_FA** - `b57b212` (feat)
2. **task 2: implement MMS_FA forced alignment pipeline** - `fd3356e` (test) + `513ca28` (feat)
3. **task 3: add align forced CLI command and Taskfile target** - `7848b02` (feat)

**Plan metadata:** *(pending)* (docs: complete plan)

_Note: TDD task 2 has two commits (RED test → GREEN implementation)_

## Files Created/Modified
- `bibliavox/config.py` — Updated ModelConfig type literal, gauntlet models (4 correct models), openai_api_key field
- `docker/Dockerfile.align` — Added torchaudio MMS_FA compatibility comment
- `bibliavox/align/forced.py` — MMS_FA forced alignment pipeline: align_verse, align_chapter, save_forced_alignment
- `tests/test_forced.py` — 10 tests covering align_verse, align_chapter, save_forced_alignment
- `bibliavox/cli/align.py` — Added `forced` command with MEK verse loading, Rich table output
- `Taskfile.yml` — Added align:forced and align:forced-all targets

## Decisions Made
- Replaced SZTAKI-HLT/hubert-base-cc-hu (text BERT, not audio) with facebook/mms-1b-fl102 and sarpba/wav2vec2-large-xlsr-53-hungarian per D-24
- Default gauntlet order: ASR models first (faster-whisper, VibeVoice), then forced alignment models (MMS_FA, wav2vec2) per D-29
- Used `with_star=True` for MMS_FA model to handle transcript mismatches (intro narration, digit differences)
- Standalone MMS_FA pipeline (not hybrid with RapidFuzz) per D-06 executor discretion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed mock chain for torchaudio MMS_FA tests**
- **Found during:** task 2 (implement MMS_FA forced alignment pipeline)
- **Issue:** torch and torchaudio not installed locally (only in Docker), so module-level imports failed and mock patching couldn't find module attributes
- **Fix:** Used try/except for module-level imports with None fallback, rewrote tests with proper mock chain helper to handle `.to(device)` call chaining
- **Files modified:** tests/test_forced.py, bibliavox/align/forced.py
- **Verification:** All 10 tests pass with mocked GPU operations
- **Committed in:** 513ca28 (task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Mock infrastructure fix necessary for testability. No scope creep.

## Issues Encountered
- torch/torchaudio not available in host environment (only in Docker) — resolved with try/except imports and comprehensive mocking

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MMS_FA forced alignment pipeline ready for Phase 6 calibration comparison
- Phone-level and verse-level output available at data/aligned/mms_fa/
- Gauntlet config corrected with 4 proper audio models for model comparison

---
*Phase: 05-forced-alignment-and-alternatives*
*Completed: 2026-06-02*

## Self-Check: PASSED

All files verified present. All commits verified in git log.
