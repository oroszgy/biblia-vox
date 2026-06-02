# Phase 5: Forced Alignment & Alternatives - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Secondary alignment tier (MMS forced alignment) and exploratory approaches (VibeVoice, paid APIs) are available for comparison, with CTC drift compensation for long chapters. This phase expands the alignment engine beyond faster-whisper + RapidFuzz to include forced alignment models and alternative ASR approaches, enabling informed model selection in Phase 6.
</domain>

<decisions>
## Implementation Decisions

### MMS_FA Integration
- **D-01:** Separate `align forced` CLI command. Keeps forced alignment separate from whisper-based alignment.
- **D-02:** Both output formats: verse-level timestamps (matching existing match.py output) AND raw phone-level timestamps for granular analysis.
- **D-03:** Docker container (consistent with Phase 4 pattern for GPU models).
- **D-04:** Use existing JSONL corpora (mek.jsonl) as text input for forced alignment.
- **D-05:** Save intermediate MMS_FA output (phone-level timestamps) to data/aligned/ for debugging and post-hoc inspection.
- **D-06:** OpenCode discretion on standalone MMS_FA pipeline vs MMS_FA + RapidFuzz hybrid.

### VibeVoice Decision
- **D-07:** Build a working VibeVoice prototype (not just documentation). Roadmap requirement: "working prototype or reasoned rejection".
- **D-08:** Docker container for VibeVoice (isolates 7B model dependencies).
- **D-09:** Try both approaches: VibeVoice ASR + RapidFuzz matching AND VibeVoice direct alignment. Compare results.
- **D-10:** Include VibeVoice results in Phase 6 comparison framework (WER + timestamp accuracy metrics).
- **D-11:** Use VibeVoice-ASR-7B model (14GB VRAM, MIT license, 50+ languages).
- **D-12:** Evaluate on same test chapters as other models for direct comparison.
- **D-13:** Add VibeVoice to model gauntlet if it performs well.
- **D-14:** Sequential execution on RTX 3090 (one model at a time due to VRAM constraints).

### CTC Drift Compensation
- **D-15:** VAD-based chunking using faster-whisper's silero-vad for natural silence boundaries.
- **D-16:** 500ms-1s overlap between chunks for continuity at boundaries.
- **D-17:** Confidence-based merge for overlapping timestamps (use confidence scores to resolve conflicts).
- **D-18:** OpenCode discretion on whether drift compensation applies to all methods or CTC-based models only.

### Paid API Evaluation
- **D-19:** Evaluate OpenAI Whisper API (standard endpoint) as reference baseline.
- **D-20:** Same gold chapters and gold standard as local models for fair comparison.
- **D-21:** $10-20 budget for API calls.
- **D-22:** Include cost per chapter in comparison report alongside quality metrics.
- **D-23:** Paid API is reference only — integration as alternative to local models deferred to potential Phase 5.5.

### Model Gauntlet Cleanup
- **D-24:** Replace SZTAKI-HLT/hubert-base-cc-hu (text BERT, not audio) with facebook/mms-1b-fl102 and sarpba/wav2vec2-large-xlsr-53-hungarian.
- **D-25:** Add systran/faster-whisper-large-v3 as primary ASR (Apache 2.0, excellent multilingual). Keep bofenghuang/whisper-large-v2-cv11-hu as backup.
- **D-26:** Add VibeVoice-ASR-7B to gauntlet configuration.
- **D-27:** Default gauntlet: faster-whisper-large-v3, VibeVoice-ASR-7B, mms-1b-fl102, wav2vec2-large-xlsr-53-hungarian.
- **D-28:** Keep BIBLIAVOX_GAUNTLET env var override for custom model lists.
- **D-29:** Run order: ASR models first, then forced alignment models.

### Evaluation Reporting
- **D-30:** JSONL for machine-readable results + Rich table for CLI display. Both formats from same data.
- **D-31:** Store evaluation results in data/evaluation/ directory.
- **D-32:** Metrics: WER (Word Error Rate), timestamp accuracy (start/end deviation), confidence scores, cost per chapter (for paid APIs).
- **D-33:** Both CLI command (`bibliavox align evaluate`) and Taskfile target (`align:evaluate`).
- **D-34:** Side-by-side comparison table for multiple model results.

### Result Caching
- **D-35:** Cache alignment results per chapter per model. Avoids re-running expensive GPU inference.
- **D-36:** Store in data/aligned/{model}/{USX}/{chapter}.json.
- **D-37:** Never invalidate cache automatically. User must manually delete to re-run.

### Error Handling
- **D-38:** Halt gauntlet on first model failure (fail-fast approach).
- **D-39:** Include failed models in evaluation report with error message. User knows what failed and why.

### OpenCode's Discretion
- Standalone MMS_FA pipeline vs MMS_FA + RapidFuzz hybrid (D-06)
- Whether drift compensation applies to all methods or CTC-only (D-18)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` — Phase 5 goal and success criteria contract
- `.planning/REQUIREMENTS.md` — ALN-03, ALN-04, ALN-05, ALN-09 definitions
- `.planning/STATE.md` — current project state, known blockers, and continuity

### Prior phase decisions to carry forward
- `.planning/phases/04-transcription-based-alignment/04-CONTEXT.md` — Docker GPU infrastructure, model gauntlet setup, faster-whisper + RapidFuzz pipeline
- `.planning/phases/04-transcription-based-alignment/04-RESEARCH.md` — Model research: MMS_FA, wav2vec2, VibeVoice specifications
- `.planning/phases/03-audio-pipeline/03-CONTEXT.md` — Audio prepared artifact paths (data/prepared/audio/{USX}/) and batch execution semantics

### Codebase analysis
- `.planning/codebase/INTEGRATIONS.md` — Current model integrations and Docker setup
- `.planning/codebase/CONCERNS.md` — Known issues: hubert-base-cc-hu is text BERT, silent model fallback

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bibliavox/config.py`: ModelGauntletSettings and gauntlet configuration to be updated
- `bibliavox/align/transcribe.py`: Transcription service with faster-whisper and VibeVoice code paths
- `bibliavox/align/match.py`: RapidFuzz matching service for verse-level timestamps
- `docker/Dockerfile.align`: Docker GPU container setup for alignment models
- `Taskfile.yml`: Task structure and dependency chaining for alignment targets

### Established Patterns
- Subcommand-oriented CLI architecture (`bibliavox align ...`) with Rich output
- Docker containers for GPU model inference (Phase 4 pattern)
- Data artifacts managed under standard directories (data/aligned/, data/evaluation/)
- Reproducible task-first workflow where commands are mirrored in Taskfile targets

### Integration Points
- `bibliavox/cli/align.py`: CLI commands for alignment (add `align forced` and `align evaluate`)
- `docker-compose.yml`: Add MMS_FA and VibeVoice services
- `bibliavox/align/`: New modules for forced alignment and evaluation
- `data/aligned/{model}/`: Cached alignment results per model
- `data/evaluation/`: Evaluation reports and comparison results

</code_context>

<specifics>
## Specific Ideas

- User wants to try both VibeVoice approaches (ASR + RapidFuzz AND direct alignment) and compare results
- Paid API integration as alternative to local models is deferred to potential Phase 5.5 (not this phase)
- Evaluation should include cost metrics per chapter for paid API comparison
- Side-by-side comparison table for easy model selection in Phase 6

</specifics>

<deferred>
## Deferred Ideas

### Paid API Integration (Potential Phase 5.5)
- If OpenAI Whisper API performs well, offer it as an alternative to local models
- Separate phase to avoid scope creep in Phase 5
- Requires cost-benefit analysis and integration design

</deferred>

---

*Phase: 05-forced-alignment-and-alternatives*
*Context gathered: 2026-06-02*
