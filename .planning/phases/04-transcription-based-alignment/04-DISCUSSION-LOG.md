# Phase 4: Transcription-Based Alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 04-transcription-based-alignment
**Areas discussed:** VAD & Silence Handling, Fuzzy Matching Granularity, LoRA Adapter Management, Model Exploration

---

## VAD & Silence Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in faster-whisper VAD (Recommended) | Let faster-whisper handle it internally using its built-in silero-vad filter | ✓ |
| Explicit pre-transcription VAD | Run a separate VAD pass first to explicitly split audio into speech segments | |

**User's choice:** Built-in faster-whisper VAD (Recommended)
**Notes:** Decided to rely on the built-in VAD for simplicity and integration.

---

## Fuzzy Matching Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Word-level matching (Recommended) | Match sequence of words to get exact word-level timestamp boundaries | ✓ |
| Character-level string matching | Match sliding window of characters; requires interpolating timestamps within the segment | |

**User's choice:** Word-level matching (Recommended)
**Notes:** Word-level granularity prevents the need for manual interpolation of timestamps.

---

## LoRA Adapter Management

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-downloaded artifact (Recommended) | Use a Taskfile target to pre-download models to a local directory before running alignment | ✓ |
| Download at runtime | Let faster-whisper download the adapter from HuggingFace at runtime if missing | |

**User's choice:** Pre-downloaded artifact (Recommended)
**Notes:** Ensures offline reproducibility and avoids runtime networking surprises.

---

## Model Exploration

| Option | Description | Selected |
|--------|-------------|----------|
| Iterative metric-based testing (Recommended) | Implement base whisper, then try specific Hungarian LoRAs one by one based on metrics | |
| Configurable model gauntlet | Provide a config file where multiple HF repos can be specified and run sequentially | ✓ |

**User's choice:** "2, plus research vibevoice, I suspect it could be a viable alternative"
**Notes:** User opted for the configurable model gauntlet and explicitly requested adding VibeVoice to the evaluation mix, predicting it might be a viable alternative.

---

## OpenCode's Discretion

- Docker/Python orchestration mechanics
- Output JSON format structure for transcriptions before fuzzy matching

## Deferred Ideas

None
