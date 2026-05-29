# Phase 3: Audio Pipeline - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the audio preparation pipeline for chapter-level Bible narration: discover/download MP3 sources, convert to WAV 16kHz mono, expose metadata, and provide accurate timestamp seek behavior for downstream alignment.

Scope is limited to audio acquisition/preparation and verification mechanics for Phase 3 requirements (AUD-01..AUD-05).

</domain>

<decisions>
## Implementation Decisions

### Source inventory and mismatch handling
- **D-01:** Default batch behavior is source-truth: when MEK chapter inventory differs from versification expectations, continue processing available chapters and emit a mismatch report.
- **D-02:** Inventory mismatches are visible diagnostics, not silent behavior. Silent skip on schema/source divergence is not allowed.

### Command contract and task UX
- **D-03:** Keep split Taskfile commands for download flows: separate single-chapter and all-chapter task targets (instead of one task with mixed mode flags as the canonical contract).
- **D-04:** Typer `audio` subcommands remain first-class, but Taskfile targets are the user-facing acceptance path for phase success criteria.

### Conversion dependency policy
- **D-05:** `ffmpeg` and `ffprobe` are required dependencies for Phase 3 runtime commands (`audio convert`, `audio info`, `audio prepare`).
- **D-06:** If required binaries are missing, commands must fail with explicit setup guidance; no best-effort degraded conversion path.

### Seek behavior contract
- **D-07:** `bibliavox audio seek` default verification behavior is playback preview for the requested timestamp window.
- **D-08:** Seek behavior must be WAV/sample based (not MP3 timebase based) so VBR drift is avoided in the verification path.

### Artifact layout and processing semantics
- **D-09:** Freeze raw/prepared split paths: MP3 under `data/raw/audio/{USX}/{chapter:03d}.mp3`; prepared outputs under `data/prepared/audio/{USX}/`.
- **D-10:** Prepared artifacts include WAV plus metadata/index sidecars for alignment-stage consumption.
- **D-11:** Batch runs default to Rich multi-progress with per-chapter status and aggregate counts.
- **D-12:** Reruns are idempotent by default (skip existing complete artifacts), with explicit `--force` override to reprocess targets.

### OpenCode's Discretion
- Exit code semantics for partial failure in batch mode (as long as mismatch diagnostics and failure summaries remain explicit)
- Internal module boundaries within `bibliavox/audio/` (discovery/downloader/convert/metadata/seek/pipeline split)
- Exact progress layout details (columns, wording, cadence)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria contract
- `.planning/REQUIREMENTS.md` — AUD-01, AUD-02, AUD-03, AUD-04, AUD-05 definitions
- `.planning/STATE.md` — current project state, known blockers, and continuity

### Prior phase decisions to carry forward
- `.planning/phases/01-foundation/01-CONTEXT.md` — Typer + Taskfile patterns and project structure conventions
- `.planning/phases/02-text-acquisition/02-CONTEXT.md` — reproducible pipeline and artifact conventions
- `.planning/phases/2.5-data-quality/02.5-CONTEXT.md` — source-truth precedence and data-quality correction approach

### Phase 3 research and validation inputs
- `.planning/phases/03-audio-pipeline/03-RESEARCH.md` — MEK inventory findings, conversion/seek recommendations
- `.planning/phases/03-audio-pipeline/03-VALIDATION.md` — Nyquist validation contract for Phase 3

### Implementation anchors in current codebase
- `bibliavox/main.py` — CLI subcommand registration pattern
- `bibliavox/cli/text.py` — Typer command style and validation/error handling conventions
- `bibliavox/config.py` — settings/path configuration entry point
- `Taskfile.yml` — existing task naming and workflow conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bibliavox/main.py`: existing `add_typer` registration pattern to extend with `audio` command group
- `bibliavox/cli/text.py`: concrete Typer + Rich patterns for argument validation, command output, and failure exits
- `bibliavox/config.py`: centralized settings object suitable for future audio path/config defaults
- `Taskfile.yml`: established quality/task conventions and dependency chaining patterns

### Established Patterns
- Subcommand-oriented CLI architecture (`reference`, `text`) with Rich output and strict argument validation
- Reproducible task-first workflow where commands are mirrored in Taskfile targets
- Data artifacts managed under `data/raw/` and `data/processed/` style directories, not ad hoc paths

### Integration Points
- Add new audio package modules under `bibliavox/audio/`
- Register `audio` Typer app in `bibliavox/main.py`
- Add `audio:*` Taskfile targets consistent with existing naming and dependency style
- Keep seek/index outputs aligned to downstream Phase 4 alignment inputs

</code_context>

<specifics>
## Specific Ideas

- Keep split download tasks as the canonical interface (single vs all-chapters flow)
- Require strict toolchain presence (`ffmpeg`/`ffprobe`) instead of permissive fallback behavior
- Seek verification should be experiential (playback preview) in addition to numerical correctness

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 03-audio-pipeline*
*Context gathered: 2026-05-29*
