# Phase 7: Export & Pipeline Integration - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert alignment results into a portable JSONL format with full metadata, and wire all pipeline stages (text → audio → alignment → export) into a single end-to-end command. This is the "last mile" that makes the pipeline usable by non-technical operators. The export produces machine-readable verse-to-audio mappings, and the pipeline orchestrates all stages with progress reporting and idempotent behavior.
</domain>

<decisions>
## Implementation Decisions

### JSONL Output Format (EXP-01)
- **D-01:** Flat rows, one per verse-model pair. Each JSONL line represents a single verse aligned by a single model.
- **D-02:** verse_ref format: "BOOK CH:VS" (e.g., "TIT 1:1"). Matches existing evaluation output convention.
- **D-03:** audio_file as canonical prepared path: `data/prepared/audio/{USX}/{chapter:03d}.wav`. Matches existing pipeline convention.
- **D-04:** Include both `canonical_text` (from source corpus) and `matched_text` (from transcription) fields. Useful for quality inspection.
- **D-05:** Include per-verse `wer` and `cer` metrics in each row. Enables downstream quality filtering.
- **D-06:** Export ALL verses including failed alignments. Failed verses have `null` timestamps and `0` confidence. No data loss.
- **D-07:** Fields per line: `verse_ref`, `audio_file`, `start_sec`, `end_sec`, `source` (model ID), `translation` ("SZIT"), `confidence` (0-1), `canonical_text`, `matched_text`, `wer`, `cer`.

### Pipeline Orchestration (EXP-02, EXP-05)
- **D-08:** Chained Taskfile targets: `export:fetch-text`, `export:prepare-audio`, `export:align`, `export:jsonl`. Pipeline target `export:run` calls them in order.
- **D-09:** Fail-fast on model failure. Stop pipeline on first failure. Matches Phase 5 D-38 decision.
- **D-10:** Default model: VibeVoice only (`microsoft/VibeVoice-ASR-HF`). User can override via `MODEL=...` Taskfile variable or `--model` CLI flag.
- **D-11:** Per-stage Rich progress bars showing stage name, chapter count, and ETA. One bar per pipeline stage.

### Gold Subset & Idempotency (EXP-05)
- **D-12:** Gold chapters defined via `BIBLIAVOX_GOLD_CHAPTERS` config setting in `bibliavox/config.py`. Default: TIT 1-3, TOB 1-4, ZEP 1-3 (10 chapters). User overrides via `.env` or env var.
- **D-13:** Chapter "completed" = export JSONL file exists AND all verses have non-null timestamps for the selected model. Thorough check prevents partial exports.
- **D-14:** `--force` flag triggers full re-run of ALL stages for forced chapters. Guarantees fresh data.

### Confidence Normalization
- **D-15:** Normalize all confidence scores to 0-1 range per model using divide-by-max method. RapidFuzz 0-100 → divide by 100. Simple and effective.
- **D-16:** Normalization applied during export, not during alignment. Raw scores preserved in alignment cache.

### Canonical Text Source
- **D-17:** Use `mek.jsonl` (35,350 verses, 73 books) as canonical text source for export. Has complete coverage vs SZIT's 66 books.

### OpenCode's Discretion
- Specific structure of the export module (new `bibliavox/export/` package or extend `bibliavox/align/`)
- Whether to include a `bibliavox export` CLI subcommand group or wire export into existing `bibliavox align`
- How to handle the Taskfile variable passing for gold chapters config

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` — Phase 7 goal and success criteria (EXP-01 through EXP-05)
- `.planning/REQUIREMENTS.md` — EXP-01 to EXP-05 definitions
- `.planning/STATE.md` — current project state, known blockers, and continuity

### Prior phase decisions to carry forward
- `.planning/phases/05-forced-alignment-and-alternatives/05-CONTEXT.md` — Evaluation engine, result caching (D-35 to D-37), JSONL + Rich table pattern (D-30)
- `.planning/phases/05-forced-alignment-and-alternatives/05-04-SUMMARY.md` — Evaluation engine with WER, timestamp accuracy, confidence, cost metrics
- `.planning/phases/04-transcription-based-alignment/04-CONTEXT.md` — Docker GPU infrastructure, model gauntlet config
- `.planning/phases/03-audio-pipeline/03-CONTEXT.md` — Audio prepared artifact paths (data/prepared/audio/{USX}/)

### Codebase analysis
- `.planning/codebase/ARCHITECTURE.md` — Data flow, component responsibilities, pipeline stages
- `.planning/codebase/INTEGRATIONS.md` — External sources, data storage layout
- `.planning/codebase/STACK.md` — Tech stack, Docker config, dependencies

### Existing evaluation data
- `data/evaluation/` — Per-chapter matched JSON with verse-level timestamps (10 gold chapters × 3 models)
- `data/evaluation/evaluation.jsonl` — Machine-readable evaluation results
- `data/evaluation/evaluation_summary.json` — Model comparison summary
- `data/processed/evaluation/` — Processed evaluation with WER/CER per chapter
- `data/processed/text/mek.jsonl` — Canonical text corpus (35,350 verses, 73 books)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bibliavox/align/evaluate.py`: Evaluation engine with WER/CER computation, result caching, comparison table — can be extended for export metrics
- `bibliavox/cli/align.py`: CLI commands with Rich output pattern — model for export CLI
- `bibliavox/config.py`: Pydantic settings with BIBLIAVOX_ prefix — add BIBLIAVOX_GOLD_CHAPTERS here
- `Taskfile.yml`: Task structure and dependency chaining — pattern for export targets

### Established Patterns
- Subcommand-oriented CLI architecture (`bibliavox ...`) with Rich output
- Data artifacts managed under standard directories (data/evaluation/, data/aligned/, data/prepared/)
- Reproducible task-first workflow where commands are mirrored in Taskfile targets
- Module-level caches with lazy loading for expensive data
- Per-chapter JSON files with verse-level alignment data

### Integration Points
- `bibliavox/cli/align.py`: Existing evaluate-gold and evaluate commands produce the data Phase 7 exports
- `bibliavox/config.py`: Add gold chapters configuration
- `Taskfile.yml`: Add export:run pipeline target
- `data/evaluation/`: Source of alignment results for export
- `data/processed/text/mek.jsonl`: Source of canonical text for export

</code_context>

<specifics>
## Specific Ideas

- User wants VibeVoice as default model for pipeline, with override capability
- Pipeline should be chained Taskfile targets (not a single CLI command)
- Export includes all verses (even failed ones) with null timestamps
- Per-verse WER/CER included in export for quality inspection
- Confidence normalized to 0-1 per model using divide-by-max

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-export-and-pipeline-integration*
*Context gathered: 2026-06-02*
