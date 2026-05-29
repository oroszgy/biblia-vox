# Phase 3: Audio Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 03-audio-pipeline
**Areas discussed:** Inventory mismatch policy, Download command contract, Conversion dependency policy, Seek behavior contract, Storage path contract, Progress reporting UX, Resume/idempotency semantics

---

## Inventory mismatch policy

| Option | Description | Selected |
|--------|-------------|----------|
| Continue + report (Recommended) | Process available chapters, emit mismatch report, non-zero only on transport/runtime failures | ✓ |
| Fail fast on mismatch | Abort immediately if any schema/source mismatch is detected | |
| Continue silently | Process what exists and do not produce explicit mismatch diagnostics | |

**User's choice:** Continue + report
**Notes:** Keep source-truth behavior while preserving explicit visibility of mismatches.

---

## Download command contract

| Option | Description | Selected |
|--------|-------------|----------|
| Single task + flags (Recommended) | Use `task audio:download --book ... --chapter ...` and `task audio:download --all --workers N` as canonical | |
| Split tasks | Keep separate targets like `audio:download` and `audio:download-all` | ✓ |
| CLI only | Treat `uv run bibliavox ...` as canonical and keep Taskfile minimal | |

**User's choice:** Split tasks
**Notes:** Preserve explicit separate task entrypoints for single and batch download workflows.

---

## Conversion dependency policy

| Option | Description | Selected |
|--------|-------------|----------|
| Require ffmpeg+ffprobe (Recommended) | Commands fail with clear setup message when missing; keeps format checks strict | ✓ |
| Fallback for info only | Require ffmpeg for convert, allow metadata fallback path for info | |
| Best-effort fallback everywhere | Allow degraded behavior for all commands if ffmpeg tools are absent | |

**User's choice:** Require ffmpeg+ffprobe
**Notes:** Prefer strict deterministic tooling over partial fallback semantics.

---

## Seek behavior contract

| Option | Description | Selected |
|--------|-------------|----------|
| Write WAV clip + metadata (Recommended) | Extract `[seconds, seconds+duration]` to output WAV and print sample/timing details | |
| Print offsets only | Report computed sample/frame offsets without writing audio clip | |
| Playback preview | Play the requested segment directly in terminal environment | ✓ |

**User's choice:** Playback preview
**Notes:** Verification path should include immediate audible confirmation.

---

## Storage path contract

| Option | Description | Selected |
|--------|-------------|----------|
| Raw+prepared split (Recommended) | MP3 in `data/raw/audio/{USX}/{chapter:03d}.mp3`, WAV/meta/index in `data/prepared/audio/{USX}/` | ✓ |
| Single tree only | Keep all MP3/WAV/meta/index under one `data/audio/` hierarchy | |
| Date-based batches | Store by run date then book/chapter for each pipeline execution | |

**User's choice:** Raw+prepared split
**Notes:** Preserve clear separation between source audio and prepared alignment artifacts.

---

## Progress reporting UX

| Option | Description | Selected |
|--------|-------------|----------|
| Rich multi-progress (Recommended) | Show per-chapter running status + aggregate totals (downloaded/skipped/failed) | ✓ |
| Compact text lines | Only log periodic counters and final summary | |
| Minimal quiet mode default | Default quiet output; verbose flag required for progress details | |

**User's choice:** Rich multi-progress
**Notes:** Batch operations should visibly communicate chapter-level and aggregate progress.

---

## Resume/idempotency semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Skip existing + --force override (Recommended) | Default skip complete artifacts; `--force` re-download/re-convert/re-index target chapters | ✓ |
| Always reprocess | Every run replaces existing outputs, no skip behavior | |
| Prompt per chapter | Interactive prompt for each existing chapter output | |

**User's choice:** Skip existing + --force override
**Notes:** Keep reruns deterministic and non-interactive by default.

---

## OpenCode's Discretion

- Exact exit-code threshold for partial batch failures
- Internal module boundaries under `bibliavox/audio/`
- Rich progress presentation details

## Deferred Ideas

None.
