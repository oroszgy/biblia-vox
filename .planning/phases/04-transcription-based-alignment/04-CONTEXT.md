# Phase 4: Transcription-Based Alignment - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Locate verses in audio via faster-whisper transcription with a Hungarian LoRA adapter, followed by fuzzy text matching against known verse text. Includes setting up Docker infrastructure for GPU models to isolate CUDA/PyTorch dependencies and configuring it for local NVIDIA RTX 3090 passthrough.
</domain>

<decisions>
## Implementation Decisions

### VAD & Silence Handling
- **D-01:** Let faster-whisper handle silence detection internally using its built-in silero-vad filter to prevent phantom verse matches. No separate pre-transcription VAD pass required.

### Fuzzy Matching Granularity
- **D-02:** RapidFuzz should match at the word-level (matching sequence of words/tokens) to obtain exact word-level timestamp boundaries, rather than character-level string matching.

### LoRA Adapter Management
- **D-03:** Use a Taskfile target to pre-download the Hungarian LoRA adapter model files to a local directory as artifacts before running alignment. Do not download on the fly at runtime.

### Model Exploration & Selection
- **D-04:** Implement a configurable model gauntlet where multiple HuggingFace repositories can be specified in a config file and run sequentially for testing and metrics gathering.
- **D-05:** Research VibeVoice as part of this configurable model gauntlet to determine if it is a viable alternative model (user specifically requested testing it here, pulling it forward from Phase 5).

### OpenCode's Discretion
- Specifics of the docker-compose setup and how Python interacts with the Docker container for execution logic versus orchestration.
- Output JSON format structure for the intermediate transcriptions before matching.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` — Phase 4 goal and success criteria contract
- `.planning/REQUIREMENTS.md` — ALN-01, ALN-02, ALN-08, INF-01, INF-03, INF-04, INF-05 definitions
- `.planning/STATE.md` — current project state, known blockers, and continuity

### Prior phase decisions to carry forward
- `.planning/phases/02-text-acquisition/02-CONTEXT.md` — text artifact structures
- `.planning/phases/03-audio-pipeline/03-CONTEXT.md` — Audio prepared artifact paths (`data/prepared/audio/{USX}/`) and batch execution semantics
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Taskfile.yml`: Task structure and dependency chaining for the pre-download models target.
- `bibliavox/config.py`: Configuration module to be extended with the model gauntlet settings.

### Established Patterns
- Subcommand-oriented CLI architecture (`bibliavox align ...`) with Rich output.
- Data artifacts managed under standard directories. Model artifacts should likely be placed in `data/models/`.
- Reproducible task-first workflow where commands are mirrored in Taskfile targets.

### Integration Points
- `docker/` and `docker-compose.yml` to be created for the GPU tasks, passing through the RTX 3090.
- `bibliavox/align/` to be created for transcription and matching logic.
</code_context>

<specifics>
## Specific Ideas

- The user wants a configurable setup where multiple models can be specified and evaluated in sequence, rather than hardcoding a single Hungarian LoRA immediately.
- Evaluate VibeVoice explicitly as it was suspected by the user to be a strong viable alternative.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 04-transcription-based-alignment*
*Context gathered: 2026-05-31*
