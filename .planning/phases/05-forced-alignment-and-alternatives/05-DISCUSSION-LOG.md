# Phase 5: Forced Alignment & Alternatives - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-02
**Phase:** 05-forced-alignment-and-alternatives
**Areas discussed:** MMS_FA integration, VibeVoice decision, CTC drift compensation, Paid API evaluation, Model gauntlet cleanup, Evaluation reporting format, Result caching strategy, Error handling in gauntlet

---

## MMS_FA Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Separate `align forced` command | New `bibliavox align forced` subcommand. Keeps forced alignment separate from whisper-based alignment. Clean separation of concerns. | ✓ |
| Flag on existing `align transcribe` | Add `--method forced` flag to existing `align transcribe` command. Reuses existing CLI structure but mixes concerns. | |

**User's choice:** Separate `align forced` command
**Notes:** Clean separation of concerns preferred.

| Option | Description | Selected |
|--------|-------------|----------|
| Match existing match.py output format | Same format as whisper alignment: {verse_id, start_sec, end_sec, confidence_score}. Allows direct comparison with Phase 4 results. | ✓ |
| Raw MMS_FA phone-level output | Raw MMS_FA output with phone-level timestamps. More granular but incompatible with existing pipeline. | ✓ |

**User's choice:** Both formats
**Notes:** User wants verse-level timestamps matching existing pipeline output, plus raw phone-level timestamps for granular analysis.

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone MMS_FA pipeline | MMS_FA handles the full pipeline: audio → text alignment → verse timestamps. Simpler but less flexible. | |
| MMS_FA + RapidFuzz hybrid | MMS_FA provides forced alignment, then RapidFuzz matches verses. Reuses existing match.py but adds complexity. | |
| You decide | Let OpenCode decide based on MMS_FA architecture. | ✓ |

**User's choice:** You decide
**Notes:** OpenCode discretion on implementation approach.

| Option | Description | Selected |
|--------|-------------|----------|
| torchaudio Python API | Use `torchaudio.pipelines.MMS_FA` directly in Python. Native integration, no Docker overhead for this model. | |
| Docker container | Run MMS_FA in Docker container like faster-whisper. Consistent with Phase 4 pattern but heavier. | ✓ |

**User's choice:** Docker container
**Notes:** Consistent with Phase 4 GPU model pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| Use existing JSONL corpora as text input | MMS_FA is a forced alignment model that needs both audio and text as input. The text should come from the already-ingested Bible JSONL corpora (mek.jsonl). | ✓ |
| Separate text input flag | Require the user to provide text separately. More flexible but redundant. | |

**User's choice:** Use existing JSONL corpora as text input
**Notes:** Leverage existing data infrastructure.

| Option | Description | Selected |
|--------|-------------|----------|
| Save intermediate output | Save intermediate MMS_FA output (phone-level timestamps) to data/aligned/ for debugging and analysis. Allows post-hoc inspection. | ✓ |
| Final output only | Only produce final verse-level timestamps. Smaller footprint but less debuggability. | |

**User's choice:** Save intermediate output
**Notes:** Debuggability preferred over storage savings.

---

## VibeVoice Decision

| Option | Description | Selected |
|--------|-------------|----------|
| Working prototype | Build a working VibeVoice prototype that produces verse-level timestamps. Full evaluation with metrics comparison against faster-whisper. | ✓ |
| Documented assessment only | Document feasibility based on Phase 4 research without building a prototype. Faster but less rigorous. | |
| Drop VibeVoice | Drop VibeVoice entirely. Focus on MMS_FA and paid APIs instead. | |

**User's choice:** Working prototype
**Notes:** Roadmap requirement: "working prototype or reasoned rejection".

| Option | Description | Selected |
|--------|-------------|----------|
| Docker container | Run VibeVoice in Docker container like faster-whisper. Consistent with Phase 4 pattern, isolates 7B model dependencies. | ✓ |
| Local Python | Run locally with torch. Faster iteration but requires local CUDA setup. | |

**User's choice:** Docker container
**Notes:** Consistent with Phase 4 GPU model pattern.

| Option | Description | Selected |
|--------|-------------|----------|
| VibeVoice ASR + RapidFuzz matching | VibeVoice produces ASR output with timestamps. Use RapidFuzz to match verses against transcribed text (same as faster-whisper pipeline). | ✓ |
| VibeVoice direct alignment | Use VibeVoice's built-in timestamping if available. More integrated but less flexible. | ✓ |

**User's choice:** Try both approaches and compare
**Notes:** User wants to evaluate both approaches to determine which works better.

| Option | Description | Selected |
|--------|-------------|----------|
| Include in comparison metrics | Save VibeVoice evaluation metrics alongside MMS_FA and faster-whisper results for Phase 6 comparison. | ✓ |
| Separate evaluation | Keep VibeVoice results separate. Different evaluation framework. | |

**User's choice:** Include in comparison metrics
**Notes:** Feed into Phase 6 comparison framework.

| Option | Description | Selected |
|--------|-------------|----------|
| VibeVoice-ASR-7B | Use `VibeVoice-ASR-7B` as identified in Phase 4 research. 14GB VRAM, MIT license, 50+ languages. | ✓ |
| Smaller variant | Use a smaller VibeVoice variant if available. Less VRAM but potentially lower quality. | |

**User's choice:** VibeVoice-ASR-7B
**Notes:** Full model as identified in Phase 4 research.

| Option | Description | Selected |
|--------|-------------|----------|
| Same test chapters | Run VibeVoice on the same chapters as MMS_FA and faster-whisper for direct comparison. | ✓ |
| Subset of chapters | Run VibeVoice on a subset of chapters. Faster but less comprehensive. | |

**User's choice:** Same test chapters
**Notes:** Direct comparison with other models.

| Option | Description | Selected |
|--------|-------------|----------|
| Add to gauntlet | If VibeVoice performs well, add it as a permanent option in the model gauntlet alongside faster-whisper. | ✓ |
| One-off evaluation | Keep VibeVoice as a one-off evaluation. Don't integrate into gauntlet. | |

**User's choice:** Add to gauntlet
**Notes:** If performs well, integrate permanently.

| Option | Description | Selected |
|--------|-------------|----------|
| WER + timestamp accuracy | WER (Word Error Rate) and timestamp accuracy against gold standard. Same metrics as other models. | ✓ |
| WER only | WER only. Simpler but less comprehensive. | |

**User's choice:** WER + timestamp accuracy
**Notes:** Same metrics as other models for fair comparison.

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential execution | VibeVoice-ASR-7B needs ~14GB VRAM. RTX 3090 has 24GB. Can run alongside other models sequentially. | ✓ |
| Parallel execution | Run multiple models in parallel if VRAM allows. Faster but more complex. | |

**User's choice:** Sequential execution
**Notes:** One model at a time due to VRAM constraints.

---

## CTC Drift Compensation

| Option | Description | Selected |
|--------|-------------|----------|
| VAD-based chunking | Use VAD (Voice Activity Detection) to detect silence boundaries. Natural break points in audio. Align each chunk independently. | ✓ |
| Fixed time windows | Fixed time windows (e.g., 5-minute chunks). Simpler but may split mid-sentence. | |

**User's choice:** VAD-based chunking
**Notes:** Natural silence boundaries preferred over arbitrary time windows.

| Option | Description | Selected |
|--------|-------------|----------|
| 500ms-1s overlap | 500ms-1s overlap between chunks. Ensures continuity at boundaries without significant redundancy. | ✓ |
| No overlap | No overlap. Simpler but may miss words at boundaries. | |
| 2-3s overlap | Longer overlap (2-3s). More redundant but safer. | |

**User's choice:** 500ms-1s overlap
**Notes:** Balance between continuity and redundancy.

| Option | Description | Selected |
|--------|-------------|----------|
| Confidence-based merge | Merge timestamps by taking the best alignment from overlapping regions. Use confidence scores to resolve conflicts. | ✓ |
| Boundary averaging | Simple boundary averaging. Less robust but simpler. | |

**User's choice:** Confidence-based merge
**Notes:** Use confidence scores to resolve conflicts at boundaries.

| Option | Description | Selected |
|--------|-------------|----------|
| Use faster-whisper silero-vad | Reuse the existing faster-whisper VAD filter. Consistent with Phase 4 approach. | ✓ |
| Separate VAD model | Use a separate VAD model (e.g., pyannote.audio). More flexible but adds dependency. | |

**User's choice:** Use faster-whisper silero-vad
**Notes:** Consistent with Phase 4 approach.

| Option | Description | Selected |
|--------|-------------|----------|
| All methods | Apply drift compensation to all alignment methods (faster-whisper, MMS_FA, VibeVoice). Consistent behavior. | |
| CTC-based models only | Only for CTC-based models (MMS_FA, wav2vec2). Whisper models have less drift. | |
| You decide | Let OpenCode decide. | ✓ |

**User's choice:** You decide
**Notes:** OpenCode discretion on scope of drift compensation.

---

## Paid API Evaluation

| Option | Description | Selected |
|--------|-------------|----------|
| Google Speech-to-Text | Google Speech-to-Text V2. Best multilingual support, good Hungarian. ~$0.006/15s. | |
| Azure Speech | Azure Speech Services. Competitive pricing, good Hungarian support. | |
| AWS Transcribe | AWS Transcribe. Good but less Hungarian-specific. | |
| OpenAI Whisper API | OpenAI Whisper API. Simple, good quality, ~$0.006/min. | ✓ |

**User's choice:** OpenAI Whisper API
**Notes:** Simple, well-documented, good quality.

| Option | Description | Selected |
|--------|-------------|----------|
| Same gold chapters | Run on the same gold chapters as local models. Direct comparison possible. | ✓ |
| Smaller subset | Run on a smaller subset. Saves cost but less comprehensive. | |

**User's choice:** Same gold chapters
**Notes:** Direct comparison with local models.

| Option | Description | Selected |
|--------|-------------|----------|
| Same gold standard | Use the same gold standard as local models. Fair comparison. | ✓ |
| Different criteria | Use different evaluation criteria. API has different capabilities. | |

**User's choice:** Same gold standard
**Notes:** Fair comparison with local models.

| Option | Description | Selected |
|--------|-------------|----------|
| $50 budget | Spend up to $50 on API calls for evaluation. Enough for several chapters. | |
| $10-20 budget | Minimal budget ($10-20). Just a few chapters. | ✓ |
| $100+ budget | Higher budget ($100+). More comprehensive evaluation. | |

**User's choice:** $10-20 budget
**Notes:** Minimal budget for initial evaluation.

| Option | Description | Selected |
|--------|-------------|----------|
| Include cost metrics | Include cost per chapter in the comparison report. Helps decide if paid API is worth it. | ✓ |
| Quality only | Only compare quality metrics. Cost is secondary. | |

**User's choice:** Include cost metrics
**Notes:** Cost per chapter helps decision-making.

| Option | Description | Selected |
|--------|-------------|----------|
| Offer as alternative | If OpenAI Whisper API performs well, offer it as an alternative to local models. | |
| Reference only | Keep paid API as reference only. Don't integrate. | ✓ |

**User's choice:** Reference only (maybe in separate phase 5.5)
**Notes:** Paid API integration deferred to potential Phase 5.5.

| Option | Description | Selected |
|--------|-------------|----------|
| Standard Whisper API | Use OpenAI's standard Whisper API endpoint. Simple, well-documented. | ✓ |
| Azure OpenAI Whisper | Use Whisper via Azure OpenAI. Different pricing. | |

**User's choice:** Standard Whisper API
**Notes:** Simple, well-documented endpoint.

---

## Model Gauntlet Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with MMS + wav2vec2 | Replace hubert-base-cc-hu with facebook/mms-1b-fl102 and sarpba/wav2vec2-large-xlsr-53-hungarian. Both are actual audio models. | ✓ |
| Remove only, don't replace | Remove hubert-base-cc-hu entirely. Only keep faster-whisper models. | |

**User's choice:** Replace with MMS + wav2vec2
**Notes:** Replace broken text model with actual audio models.

| Option | Description | Selected |
|--------|-------------|----------|
| Add faster-whisper-large-v3 | Add systran/faster-whisper-large-v3 as primary ASR (Apache 2.0, excellent multilingual). Replace gated bofenghuang model. | ✓ |
| Keep bofenghuang as primary | Keep bofenghuang model as primary. It's Hungarian-tuned. | |

**User's choice:** Add faster-whisper-large-v3 as primary, keep bofenghuang as backup
**Notes:** Primary ASR with excellent multilingual support, Hungarian-tuned as backup.

| Option | Description | Selected |
|--------|-------------|----------|
| Add VibeVoice to gauntlet | Add VibeVoice-ASR-7B to the gauntlet alongside faster-whisper models. Full model comparison. | ✓ |
| Keep VibeVoice separate | Keep VibeVoice separate. Only evaluate it in Phase 5 prototype. | |

**User's choice:** Add VibeVoice to gauntlet
**Notes:** Full model comparison in gauntlet.

| Option | Description | Selected |
|--------|-------------|----------|
| Full gauntlet as default | Default gauntlet: faster-whisper-large-v3, VibeVoice-ASR-7B, mms-1b-fl102, wav2vec2-large-xlsr-53-hungarian. Comprehensive. | ✓ |
| Minimal default | Minimal default: faster-whisper-large-v3 only. User adds others via env var. | |

**User's choice:** Full gauntlet as default
**Notes:** Comprehensive default configuration.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep env var override | BIBLIAVOX_GAUNTLET env var overrides default model list. Keep this extensibility. | ✓ |
| Hardcode models | Hardcode model list. Simpler but less flexible. | |

**User's choice:** Keep env var override
**Notes:** Maintain extensibility via environment variable.

| Option | Description | Selected |
|--------|-------------|----------|
| ASR then forced alignment | Default order: faster-whisper-large-v3 → VibeVoice-ASR-7B → mms-1b-fl102 → wav2vec2. ASR first, then forced alignment. | ✓ |
| Smallest first | Smallest model first. Minimize VRAM usage. | |

**User's choice:** ASR then forced alignment
**Notes:** Logical order: ASR models first, then forced alignment models.

---

## Evaluation Reporting Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSONL + Rich table | JSONL for machine-readable results, Rich table for CLI display. Both formats from same data. | ✓ |
| JSONL only | JSONL only. Simpler, machine-readable. | |
| Rich table only | Rich table only. Human-readable CLI output. | |

**User's choice:** JSONL + Rich table
**Notes:** Both machine-readable and human-readable formats.

| Option | Description | Selected |
|--------|-------------|----------|
| data/evaluation/ | Store evaluation results in data/evaluation/ directory. Organized by model and chapter. | ✓ |
| data/aligned/evaluation/ | Store in data/aligned/ alongside alignment results. Keeps related data together. | |

**User's choice:** data/evaluation/
**Notes:** Separate directory for evaluation reports.

| Option | Description | Selected |
|--------|-------------|----------|
| WER + timestamps + confidence + cost | WER (Word Error Rate), timestamp accuracy (start/end deviation), confidence scores, cost per chapter (for paid APIs). | ✓ |
| WER + timestamps only | WER and timestamp accuracy only. Simpler. | |

**User's choice:** WER + timestamps + confidence + cost
**Notes:** Comprehensive metrics including cost for paid API comparison.

| Option | Description | Selected |
|--------|-------------|----------|
| New evaluate command | CLI command `bibliavox align evaluate` runs evaluation and generates report. Consistent with existing CLI patterns. | |
| Taskfile target | Taskfile target `align:evaluate`. Consistent with task-based workflow. | |
| Both | Both CLI command and Taskfile target. | ✓ |

**User's choice:** Both
**Notes:** CLI command and Taskfile target for flexibility.

| Option | Description | Selected |
|--------|-------------|----------|
| Side-by-side comparison table | Compare all models side-by-side in a single Rich table. Easy to see which model performs best. | ✓ |
| Separate tables per model | Separate tables per model. More detailed but harder to compare. | |

**User's choice:** Side-by-side comparison table
**Notes:** Easy comparison across models.

---

## Result Caching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Cache per chapter per model | Cache alignment results per chapter per model. Avoids re-running expensive GPU inference. | ✓ |
| Cache per chapter | Cache per chapter only. One result per chapter regardless of model. | |
| No caching | No caching. Always re-run inference. Simpler but slower. | |

**User's choice:** Cache per chapter per model
**Notes:** Avoid re-running expensive GPU inference.

| Option | Description | Selected |
|--------|-------------|----------|
| data/aligned/{model}/ | Store in data/aligned/{model}/{USX}/{chapter}.json. Organized by model and chapter. | ✓ |
| data/.cache/alignment/ | Store in data/.cache/alignment/. Separate cache directory. | |

**User's choice:** data/aligned/{model}/
**Notes:** Organized by model and chapter.

| Option | Description | Selected |
|--------|-------------|----------|
| Invalidate on model change | If model config or version changes, invalidate cache. Ensures results match current model. | |
| Never invalidate | Never invalidate. User must manually delete cache. | ✓ |

**User's choice:** Never invalidate
**Notes:** User must manually delete cache to re-run.

---

## Error Handling in Gauntlet

| Option | Description | Selected |
|--------|-------------|----------|
| Continue with remaining models | Continue with remaining models. Log failure, skip model, proceed to next. Don't halt entire gauntlet. | |
| Halt on failure | Halt gauntlet on first failure. Fail-fast approach. | ✓ |

**User's choice:** Halt on failure
**Notes:** Fail-fast approach preferred.

| Option | Description | Selected |
|--------|-------------|----------|
| Include failures in report | Include failed models in report with error message. User knows what failed and why. | ✓ |
| Successful models only | Only include successful models. Cleaner report. | |

**User's choice:** Include failures in report
**Notes:** User wants to know what failed and why.

---

## OpenCode's Discretion

- Standalone MMS_FA pipeline vs MMS_FA + RapidFuzz hybrid (D-06)
- Whether drift compensation applies to all methods or CTC-only (D-18)

## Deferred Ideas

### Paid API Integration (Potential Phase 5.5)
- If OpenAI Whisper API performs well, offer it as an alternative to local models
- Separate phase to avoid scope creep in Phase 5
- Requires cost-benefit analysis and integration design
