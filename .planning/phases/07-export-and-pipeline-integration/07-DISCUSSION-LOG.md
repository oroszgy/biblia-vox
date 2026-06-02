# Phase 7: Export & Pipeline Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 07-export-and-pipeline-integration
**Areas discussed:** JSONL output format, Pipeline orchestration, Gold subset & idempotency, Confidence normalization

---

## JSONL Output Format

### Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat per-verse-model rows | verse_ref as 'BOOK CH:VS', audio_file as relative path, source = model ID, translation = 'SZIT', confidence = normalized 0-1. One row per verse-model pair. | ✓ |
| Flat per-verse rows (best model) | verse_ref as 'BOOK_CH_VS', audio_file as canonical path, source = alignment approach name, confidence = raw. One row per verse, best model selected. | |
| Nested per-verse with model array | One JSONL line per verse with ALL model results as an array. Lets downstream pick the best. | |

**User's choice:** Flat per-verse-model rows
**Notes:** One row per verse-model pair. Simple, machine-readable, easy to filter.

### Audio file format

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical prepared path | data/prepared/audio/{USX}/{chapter:03d}.wav — matches existing pipeline convention | ✓ |
| Relative filename only | Just the filename (e.g., '001.wav'), let downstream resolve the path | |

**User's choice:** Canonical prepared path
**Notes:** Matches existing data/prepared/audio/{USX}/{chapter:03d}.wav convention.

### Verse reference format

| Option | Description | Selected |
|--------|-------------|----------|
| BOOK CH:VS (e.g., TIT 1:1) | Matches existing evaluation output and roadmap references | ✓ |
| BOOK_CH_VS (e.g., TIT_1_1) | USX-style with underscores, matches data directory naming | |
| BOOKCHVS (e.g., TIT01001) | Compact, no spaces, easy to parse programmatically | |

**User's choice:** BOOK CH:VS (e.g., TIT 1:1)
**Notes:** Matches existing convention used in evaluation output.

### Text fields in export

| Option | Description | Selected |
|--------|-------------|----------|
| No text fields | Minimal export — just metadata fields. Smaller file size. | |
| Include both canonical and matched text | Include canonical_text (from source) and matched_text (from transcription). Useful for quality inspection. | ✓ |
| Include matched_text only | Just the matched transcription text. Helps debug alignment quality. | |

**User's choice:** Include both canonical and matched text
**Notes:** Useful for quality inspection and debugging alignment.

### Failed verse handling

| Option | Description | Selected |
|--------|-------------|----------|
| Only aligned verses | Skip verses where alignment failed or had 0% coverage. | |
| All verses (null for failed) | Include all verses from canonical text, even if alignment failed. Mark with null timestamps and 0 confidence. | ✓ |
| CLI flag (--strict) | Default includes all, --strict filters to aligned only. | |

**User's choice:** All verses (null for failed)
**Notes:** No data loss. Export includes all verses regardless of alignment success.

### Per-verse metrics

| Option | Description | Selected |
|--------|-------------|----------|
| No metrics in export | Keep export focused on timestamps and metadata. Phase 6 handles comparison. | |
| Include per-verse WER/CER | Include per-verse WER and CER in each row. Useful for quality filtering. | ✓ |
| Confidence only | Just the confidence score (already decided). | |

**User's choice:** Include all (per-verse WER and CER)
**Notes:** Enables downstream quality filtering and inspection.

---

## Pipeline Orchestration

### Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Single end-to-end command | Single `bibliavox pipeline run --gold` command orchestrating all stages. | |
| Chained Taskfile targets | Separate Taskfile targets (export:fetch-text, export:prepare-audio, export:align, export:jsonl) chained via dependencies. | ✓ |
| Both CLI and Taskfile | Both — single CLI command for operators AND composable Taskfile targets. | |

**User's choice:** Chained Taskfile targets
**Notes:** Taskfile targets chained together. User runs `task export:run` which calls them in order.

### Model failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-fast | Stop pipeline on first model failure. User sees which model failed. | ✓ |
| Continue with partial results | Continue with remaining models, mark failed ones in output. | |
| CLI flag (--fail-fast) | Default continues, --fail-fast stops on first failure. | |

**User's choice:** Fail-fast
**Notes:** Matches Phase 5 D-38 decision. Stop and report immediately.

### Default model selection

| Option | Description | Selected |
|--------|-------------|----------|
| All gauntlet models | Run all 4 models. MMS_FA will fail on Hungarian — expected. | |
| Best model only | Only run best-performing model from Phase 5 evaluation. | |
| CLI flag (--model) | Default to all, let user specify --model for single model. | |

**User's choice:** Best model only (VibeVoice), with --model override
**Notes:** Default is VibeVoice (microsoft/VibeVoice-ASR-HF). User can override via MODEL=... or --model flag.

### Progress reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Per-stage progress bars | One progress bar per stage (text fetch, audio prepare, alignment, export). Stage name updates as pipeline advances. | ✓ |
| Single overall progress bar | Single progress bar with stage indicators. Simpler but less granular. | |
| Nested progress bars | Outer bar for stages, inner bar for chapters within each stage. Most detailed but complex. | |

**User's choice:** Per-stage progress bars
**Notes:** Rich progress bars with stage indicators and ETA per stage.

---

## Gold Subset & Idempotency

### Gold subset definition

| Option | Description | Selected |
|--------|-------------|----------|
| Config setting | Add BIBLIAVOX_GOLD_CHAPTERS config setting (list of BOOK CHAPTER pairs). Default: TIT 1-3, TOB 1-4, ZEP 1-3. | ✓ |
| JSON file | File at data/reference/gold_chapters.json with list of {book, chapter} pairs. | |
| Config + CLI flags | Both — config setting for default, CLI flag --gold to use config, --book/--chapter for override. | |

**User's choice:** Config setting
**Notes:** BIBLIAVOX_GOLD_CHAPTERS in config.py with default value. Override via .env or env var.

### Completion definition

| Option | Description | Selected |
|--------|-------------|----------|
| JSONL exists + all timestamps | Chapter is 'complete' if export JSONL exists AND all verses have non-null timestamps for selected model. | ✓ |
| Export JSONL exists | Chapter is 'complete' if export JSONL exists. Simpler but may skip partial exports. | |
| Alignment cache exists | Chapter is 'complete' if alignment cache exists. Export always regenerated from cache. | |

**User's choice:** JSONL exists + all timestamps
**Notes:** Thorough check prevents partial exports from being skipped.

### Force behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Full re-run | Re-run ALL stages for forced chapters (text fetch, audio prep, alignment, export). | ✓ |
| Export only | Only re-run export stage. Assumes alignment cache is valid. | |
| Smart re-run | Re-run from the stage that produced incomplete data. Smart but complex. | |

**User's choice:** Full re-run
**Notes:** --force triggers complete pipeline re-run for affected chapters. Guarantees fresh data.

---

## Confidence Normalization

### Normalization approach

| Option | Description | Selected |
|--------|-------------|----------|
| Per-model normalization to 0-1 | Normalize all scores to 0-1 range per model. Enables cross-model comparison. | ✓ |
| Raw scores (no normalization) | Use raw scores as-is. Different models will have different scales. | |
| Phase 6 calibration | Use calibration approach from Phase 6. Most accurate but depends on Phase 6 output. | |

**User's choice:** Per-model normalization to 0-1
**Notes:** Enables cross-model comparison in the export.

### Normalization method

| Option | Description | Selected |
|--------|-------------|----------|
| Divide by max | Simple divide-by-max for each model. RapidFuzz 0-100 → divide by 100. | ✓ |
| Min-max normalization | Full min-max: (score - min) / (max - min). Handles any scale. | |
| Percentile rank | Percentile rank within each model's scores. Handles skewed distributions. | |

**User's choice:** Divide by max
**Notes:** Simple and effective. Assumes scores are on a reasonable scale already.

---

## OpenCode's Discretion

- Specific structure of the export module (new `bibliavox/export/` package or extend `bibliavox/align/`)
- Whether to include a `bibliavox export` CLI subcommand group or wire export into existing `bibliavox align`
- How to handle the Taskfile variable passing for gold chapters config

## Deferred Ideas

None — discussion stayed within phase scope.
