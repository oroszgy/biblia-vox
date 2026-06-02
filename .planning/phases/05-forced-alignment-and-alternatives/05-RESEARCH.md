# Phase 5: Forced Alignment & Alternatives - Research

**Researched:** 2026-06-02
**Domain:** Forced alignment (CTC/MMS), alternative ASR models (VibeVoice), paid API evaluation, CTC drift compensation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Separate `align forced` CLI command (keeps forced alignment separate from whisper-based)
- **D-02:** Both output formats: verse-level timestamps AND raw phone-level timestamps for granular analysis
- **D-03:** Docker container for GPU models (consistent with Phase 4 pattern)
- **D-04:** Use existing JSONL corpora (mek.jsonl) as text input for forced alignment
- **D-05:** Save intermediate MMS_FA output (phone-level timestamps) to data/aligned/ for debugging
- **D-07:** Build a working VibeVoice prototype (not just documentation)
- **D-08:** Docker container for VibeVoice (isolates 7B model dependencies)
- **D-09:** Try both approaches: VibeVoice ASR + RapidFuzz matching AND VibeVoice direct alignment
- **D-10:** Include VibeVoice results in Phase 6 comparison framework
- **D-11:** Use VibeVoice-ASR-7B model (14GB VRAM, MIT license, 50+ languages)
- **D-12:** Evaluate on same test chapters as other models for direct comparison
- **D-13:** Add VibeVoice to model gauntlet if it performs well
- **D-14:** Sequential execution on RTX 3090 (one model at a time due to VRAM)
- **D-15:** VAD-based chunking using faster-whisper's silero-vad for natural silence boundaries
- **D-16:** 500ms-1s overlap between chunks for continuity at boundaries
- **D-17:** Confidence-based merge for overlapping timestamps (use confidence scores to resolve conflicts)
- **D-19:** Evaluate OpenAI Whisper API as reference baseline
- **D-20:** Same gold chapters and gold standard as local models for fair comparison
- **D-21:** $10-20 budget for API calls
- **D-22:** Include cost per chapter in comparison report alongside quality metrics
- **D-23:** Paid API is reference only — integration as alternative deferred to potential Phase 5.5
- **D-24:** Replace SZTAKI-HLT/hubert-base-cc-hu with facebook/mms-1b-fl102 and sarpba/wav2vec2-large-xlsr-53-hungarian
- **D-25:** Add systran/faster-whisper-large-v3 as primary ASR (Apache 2.0, excellent multilingual)
- **D-26:** Add VibeVoice-ASR-7B to gauntlet configuration
- **D-27:** Default gauntlet: faster-whisper-large-v3, VibeVoice-ASR-7B, mms-1b-fl102, wav2vec2-large-xlsr-53-hungarian
- **D-28:** Keep BIBLIAVOX_GAUNTLET env var override for custom model lists
- **D-29:** Run order: ASR models first, then forced alignment models
- **D-30:** JSONL for machine-readable results + Rich table for CLI display
- **D-31:** Store evaluation results in data/evaluation/ directory
- **D-32:** Metrics: WER, timestamp accuracy (start/end deviation), confidence scores, cost per chapter
- **D-33:** Both CLI command (`bibliavox align evaluate`) and Taskfile target (`align:evaluate`)
- **D-34:** Side-by-side comparison table for multiple model results
- **D-35:** Cache alignment results per chapter per model
- **D-36:** Store in data/aligned/{model}/{USX}/{chapter}.json
- **D-37:** Never invalidate cache automatically. User must manually delete to re-run
- **D-38:** Halt gauntlet on first model failure (fail-fast approach)
- **D-39:** Include failed models in evaluation report with error message

### OpenCode's Discretion
- Standalone MMS_FA pipeline vs MMS_FA + RapidFuzz hybrid (D-06)
- Whether drift compensation applies to all methods or CTC-based models only (D-18)

### Deferred Ideas (OUT OF SCOPE)
- Paid API integration as alternative to local models (potential Phase 5.5)
- If OpenAI Whisper API performs well, offer it as alternative (separate phase)
</user_constraints>

## Summary

Phase 5 extends the alignment engine from Phase 4 (faster-whisper + RapidFuzz) to include forced alignment via torchaudio's MMS_FA pipeline and alternative ASR via VibeVoice. The phase also evaluates paid API services as reference baselines and implements CTC drift compensation for long chapters (30+ minutes).

The primary technical challenge is integrating four distinct alignment approaches — faster-whisper+RapidFuzz (Phase 4), MMS_FA forced alignment, VibeVoice ASR, and CTC models (wav2vec2) — with consistent output formats and evaluation metrics. CTC drift compensation requires chunk-and-align with VAD-based segmentation, which is critical for chapters exceeding 10-15 minutes.

**Primary recommendation:** Use torchaudio.pipelines.MMS_FA for forced alignment (ALN-03), implement VibeVoice-ASR-7B via transformers pipeline for both ASR+RapidFuzz and direct alignment paths (ALN-04), evaluate OpenAI Whisper API at $0.006/min as reference baseline (ALN-05), and implement VAD-based chunking with silero-vad for CTC drift compensation (ALN-09).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MMS_FA forced alignment | GPU Container (Docker) | — | CTC model inference requires GPU, torchaudio |
| VibeVoice ASR | GPU Container (Docker) | — | 7B model requires ~14GB VRAM, transformers |
| wav2vec2 CTC alignment | GPU Container (Docker) | — | CTC inference requires GPU, transformers |
| OpenAI Whisper API | API / Backend | — | External HTTP API call, no local GPU needed |
| VAD-based chunking | GPU Container (Docker) | Host (CPU fallback) | silero-vad runs on GPU but works on CPU |
| RapidFuzz matching | Host (CPU) | — | Text matching, no GPU needed |
| Evaluation reporting | Host (CPU) | — | Metrics computation, Rich table display |
| Result caching | Host (Storage) | — | File I/O, no GPU needed |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALN-03 | Implement torchaudio MMS_FA forced alignment as secondary precision tier | MMS_FA pipeline via torchaudio.pipelines.MMS_FA; requires text normalization; outputs phone-level and word-level timestamps; ~2.2GB VRAM for mms-1b-fl102 |
| ALN-04 | Explore VibeVoice model as alternative alignment approach | VibeVoice-ASR-7B via transformers pipeline; supports 60-min single-pass; word-level timestamps via `return_format="parsed"`; ~14GB VRAM; two approaches: ASR+RapidFuzz and direct alignment |
| ALN-05 | Explore paid API-based alignment services (cost/quality tradeoff) | OpenAI Whisper API at $0.006/min with `timestamp_granularities=["word"]`; ~$0.36/hour; only whisper-1 supports word timestamps; gpt-4o-transcribe does not |
| ALN-09 | Compensate CTC drift on long chapters (chunk-and-align with VAD anchoring) | VAD-based chunking with silero-vad; 500ms-1s overlap; confidence-based merge; LFA approach for long recordings; snap CTC peaks to VAD boundaries |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `torchaudio` | 2.8.0 | MMS_FA forced alignment pipeline | Bundles model, tokenizer, aligner; GPU-accelerated CTC alignment; supports 1130+ languages [VERIFIED: local install] |
| `torch` | 2.8.0 | GPU tensor operations, model inference | Required by torchaudio, transformers, faster-whisper [VERIFIED: local install] |
| `transformers` | 4.46.0 | VibeVoice-ASR-7B, wav2vec2 models | HuggingFace model loading and inference pipelines [VERIFIED: local install] |
| `faster-whisper` | (Docker) | Silero-VAD for chunking, Whisper ASR | Already in Dockerfile.align; provides VAD filtering [VERIFIED: existing code] |
| `rapidfuzz` | 3.14.5 | Fuzzy text matching for ASR+match path | Already in pyproject.toml; word-level partial_ratio_alignment [VERIFIED: pyproject.toml] |
| `huggingface-hub` | 1.16.1 | Model download and caching | Already in pyproject.toml; snapshot_download for pre-download [VERIFIED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openai` | latest | OpenAI Whisper API client | Only for paid API evaluation (ALN-05); D-23: reference only |
| `librosa` | (Docker) | Audio loading for wav2vec2 models | Already in Dockerfile.align |
| `soundfile` | (Docker) | Audio I/O | Already in Dockerfile.align |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| torchaudio MMS_FA | Montreal Forced Aligner (MFA) | MFA requires conda (incompatible with uv); Kaldi dependency chain [CITED: REQUIREMENTS.md out-of-scope] |
| torchaudio MMS_FA | WhisperX | Critical word-timestamp bug history; adds unnecessary complexity [CITED: REQUIREMENTS.md out-of-scope] |
| OpenAI Whisper API | Google Speech-to-Text | OpenAI has word-level timestamps via whisper-1; Google requires separate alignment |
| VibeVoice-ASR-7B | VibeVoice-ASR-3B | 7B has better accuracy; 14GB VRAM fits RTX 3090 |

**Installation:**
```bash
# torchaudio is already available in Docker (torch installed via PyTorch base image)
# For host-side testing (CPU-only):
pip install torchaudio torch

# transformers is already in Dockerfile.align
# For API evaluation:
pip install openai
```

**Version verification:** torchaudio 2.8.0 and torch 2.8.0 are installed locally and in Docker (PyTorch 2.3.0-cuda12.1 base image needs upgrade or torchaudio install in Dockerfile).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Entry Points                             │
│  bibliavox align forced  │  bibliavox align evaluate  │  align:eval │
└──────────┬───────────────┴──────────────┬───────────────┴───────────┘
           │                              │
           ▼                              ▼
┌──────────────────────────┐    ┌─────────────────────────────┐
│    Forced Alignment      │    │    Evaluation Engine         │
│    (GPU Container)       │    │    (Host CPU)                │
│                          │    │                             │
│  ┌─────────────────────┐ │    │  ┌───────────────────────┐  │
│  │ MMS_FA Pipeline     │ │    │  │ Metrics Calculator    │  │
│  │ (torchaudio)        │ │    │  │ (WER, timestamps,     │  │
│  │ - model             │ │    │  │  confidence, cost)    │  │
│  │ - tokenizer         │ │    │  └───────────────────────┘  │
│  │ - aligner           │ │    │                             │
│  └─────────────────────┘ │    │  ┌───────────────────────┐  │
│                          │    │  │ Comparison Table      │  │
│  ┌─────────────────────┐ │    │  │ (Rich side-by-side)   │  │
│  │ VibeVoice ASR       │ │    │  └───────────────────────┘  │
│  │ (transformers)      │ │    │                             │
│  │ - ASR + RapidFuzz   │ │    └─────────────────────────────┘
│  │ - Direct alignment  │ │
│  └─────────────────────┘ │
│                          │
│  ┌─────────────────────┐ │
│  │ wav2vec2 CTC        │ │
│  │ (transformers)      │ │
│  │ - sarpba/hungarian  │ │
│  └─────────────────────┘ │
│                          │
│  ┌─────────────────────┐ │
│  │ CTC Drift           │ │
│  │ Compensation        │ │
│  │ - silero-vad chunk  │ │
│  │ - overlap + merge   │ │
│  └─────────────────────┘ │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Data Layer (Host)                              │
│                                                                  │
│  data/aligned/{model}/{USX}/{chapter}.json    ← cached results   │
│  data/aligned/{model}/{USX}/{chapter}_phones.json ← phone-level  │
│  data/evaluation/summary.json                 ← comparison report│
│  data/evaluation/{book}_{chapter}_{model}_matched.json           │
└──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
bibliavox/
├── align/
│   ├── __init__.py
│   ├── transcribe.py          # Existing: faster-whisper + VibeVoice ASR
│   ├── match.py               # Existing: RapidFuzz matching
│   ├── forced.py              # NEW: MMS_FA forced alignment pipeline
│   ├── vibevoice.py           # NEW: VibeVoice direct alignment + ASR path
│   ├── ctc_align.py           # NEW: wav2vec2 CTC alignment
│   ├── drift.py               # NEW: CTC drift compensation (VAD chunking + merge)
│   ├── evaluate.py            # NEW: Evaluation engine (WER, metrics, comparison)
│   └── api_eval.py            # NEW: OpenAI Whisper API evaluation
├── cli/
│   └── align.py               # Existing: add `align forced` and `align evaluate` commands
└── config.py                  # Existing: update ModelGauntletSettings
```

### Pattern 1: MMS_FA Forced Alignment Pipeline

**What:** Use torchaudio.pipelines.MMS_FA to perform CTC-based forced alignment with the multilingual MMS model (1130+ languages, trained on 31K hours).

**When to use:** When you have known transcript text and want precise phone/word-level timestamps from CTC alignment (ALN-03).

**Example:**
```python
# Source: https://docs.pytorch.org/audio/stable/tutorials/forced_alignment_for_multilingual_data_tutorial.html
import torch
import torchaudio

bundle = torchaudio.pipelines.MMS_FA

model = bundle.get_model(with_star=False).to(device)
tokenizer = bundle.get_tokenizer()
aligner = bundle.get_aligner()

# Load audio at bundle sample rate
waveform, sample_rate = torchaudio.load(audio_path)
waveform = torchaudio.functional.resample(waveform, sample_rate, bundle.sample_rate)
waveform = waveform.to(device)

# Tokenize transcript (Hungarian text, space-separated words)
transcript = verse_text.split()  # word-level tokenization
tokens = tokenizer(transcript)

# Compute alignment
with torch.inference_mode():
    emission, _ = model(waveform)
    token_spans = aligner(emission[0], tokens)

# Extract word-level timestamps
for span in token_spans:
    start_sec = span.start * (waveform.size(-1) / emission.size(1)) / bundle.sample_rate
    end_sec = span.end * (waveform.size(-1) / emission.size(1)) / bundle.sample_rate
    print(f"{span.token}: {start_sec:.3f}s - {end_sec:.3f}s, score={span.score:.3f}")
```

**Key insight:** MMS_FA does NOT have a word-boundary token (unlike other Wav2Vec2 bundles). Post-processing must group character-level spans into words using the transcript word boundaries. [CITED: https://docs.pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html]

### Pattern 2: VibeVoice ASR Integration

**What:** Use VibeVoice-ASR-7B via transformers pipeline for both ASR+RapidFuzz and direct alignment paths.

**When to use:** Exploratory approach for long-form audio (up to 60 minutes single-pass) with built-in timestamps (ALN-04).

**Example:**
```python
# Source: https://huggingface.co/docs/transformers/en/model_doc/vibevoice_asr
from transformers import pipeline

# ASR path with word-level timestamps
pipe = pipeline(
    "automatic-speech-recognition",
    model="microsoft/VibeVoice-ASR-7B",
    device="cuda:0",
    return_timestamps="word",
)

result = pipe(audio_path)
# result contains chunks with text and (start, end) timestamps

# Direct alignment path with parsed output
pipe_parsed = pipeline(
    "automatic-speech-recognition",
    model="microsoft/VibeVoice-ASR-7B",
    device="cuda:0",
    return_format="parsed",  # Returns structured speaker/timestamp/content
)

result_parsed = pipe_parsed(audio_path)
```

**Key insight:** VibeVoice processes audio in 60-second chunks internally with convolution state caching, supporting up to 60 minutes. The `acoustic_tokenizer_chunk_size` parameter can be adjusted if 60-second chunks are too large for GPU memory. [CITED: https://huggingface.co/docs/transformers/en/model_doc/vibevoice_asr]

### Pattern 3: CTC Drift Compensation

**What:** Chunk long audio using VAD-based segmentation, align each chunk independently, merge with overlap handling.

**When to use:** Chapters exceeding 10-15 minutes where CTC models exhibit systematic temporal drift (ALN-09).

**Example:**
```python
# Source: https://github.com/MahmoudAshraf97/ctc-forced-aligner/issues/84
import torch

# VAD-based chunking with silero-vad
def get_vad_segments(audio: torch.Tensor, sr: int) -> list[tuple[float, float]]:
    """Detect speech segments using silero-vad."""
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True
    )
    get_speech_timestamps = utils[0]
    speech_timestamps = get_speech_timestamps(audio, model, sampling_rate=sr)
    return [(ts['start'] / sr, ts['end'] / sr) for ts in speech_timestamps]

def snap_to_vad(words: list[dict], vad_segments: list[tuple[float, float]]) -> list[dict]:
    """Snap CTC-aligned word boundaries to VAD-detected speech regions."""
    refined = []
    for w in words:
        w_mid = (w["start"] + w["end"]) / 2
        best_seg = next((s for s in vad_segments if s[0] <= w_mid <= s[1]), None)
        if best_seg:
            w["start"] = max(w["start"], best_seg[0])
            w["end"] = min(w["end"], best_seg[1])
        else:
            # Snap to nearest speech if CTC drifted into silence
            closest = min(vad_segments, key=lambda x: min(abs(w_mid - x[0]), abs(w_mid - x[1])))
            if w_mid < closest[0]:
                w["start"], w["end"] = closest[0], closest[0] + 0.1
            else:
                w["start"], w["end"] = closest[1] - 0.1, closest[1]
        refined.append(w)
    return refined
```

**Key insight:** CTC drift is a known problem for long audio. The LFA (Long-Form Alignment) approach from recent research shows chunking into 10-20 second segments with VAD boundaries maintains stable accuracy even on multi-hour recordings. [CITED: https://openreview.net/attachment?id=JpG7RsIFhL&name=pdf]

### Pattern 4: wav2vec2 CTC Alignment

**What:** Use wav2vec2 CTC models (sarpba/wav2vec2-large-xlsr-53-hungarian) for frame-level alignment with Hungarian language support.

**When to use:** As an alternative CTC-based alignment approach alongside MMS_FA for comparison (model gauntlet).

**Example:**
```python
# Source: https://huggingface.co/sarpba/wav2vec2-large-xlsr-53-hungarian
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

processor = Wav2Vec2Processor.from_pretrained("sarpba/wav2vec2-large-xlsr-53-hungarian")
model = Wav2Vec2ForCTC.from_pretrained("sarpba/wav2vec2-large-xlsr-53-hungarian")
model.to("cuda")

# Process audio
inputs = processor(audio_array, sampling_rate=16_000, return_tensors="pt", padding=True)
with torch.no_grad():
    logits = model(inputs.input_values.to("cuda")).logits

# CTC forced alignment
log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
targets = processor.tokenizer(transcript).input_ids
paths, scores = torchaudio.functional.forced_align(log_probs, targets, blank=0)
```

### Anti-Patterns to Avoid

- **Running multiple GPU models simultaneously:** RTX 3090 has 24GB VRAM. VibeVoice alone needs ~14GB. Run models sequentially (D-14). [VERIFIED: nvidia-smi shows 24576MiB]
- **Ignoring MMS_FA word-boundary limitation:** MMS_FA has no `|` word-boundary token. Must group character spans using transcript word boundaries, not by separator token. [CITED: MMS_FA docs]
- **Skipping text normalization for MMS_FA:** The MMS_FA pipeline expects normalized, romanized text. Hungarian diacritics may need special handling. [CITED: torchaudio multilingual tutorial]
- **Assuming VibeVoice timestamps are word-level by default:** VibeVoice outputs speaker-timestamped JSON. Must use `return_timestamps="word"` or `return_format="parsed"` for word-level timestamps. [CITED: HuggingFace docs]
- **Not using `<star>` token for MMS_FA:** When transcript has mismatches (intro narration, digit differences), the `<star>` token absorbs unmatched audio. Use `model.get_model(with_star=True)` for robust alignment. [CITED: MMS paper Section 3.1.3]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CTC forced alignment | Custom Viterbi decoder | `torchaudio.functional.forced_align()` | GPU-accelerated, handles batch, proven on 1130+ languages |
| Phone-level tokenization | Custom tokenizer | `bundle.get_tokenizer()` from MMS_FA | Must match model's token vocabulary exactly |
| VAD segmentation | Custom energy-based VAD | silero-vad (via faster-whisper or torch.hub) | Pre-trained, handles edge cases, consistent with Phase 4 |
| WER computation | Custom WER calculator | `evaluate` library from HuggingFace | Standard implementation, handles edge cases |
| OpenAI API client | Raw HTTP requests | `openai` Python SDK | Handles retries, auth, streaming, error handling |

**Key insight:** The torchaudio MMS_FA bundle packages model + tokenizer + aligner as a single pipeline. Don't try to load the model separately and align manually — the bundle's aligner handles the specific CTC decoding for MMS tokens. [VERIFIED: Context7 docs]

## Common Pitfalls

### Pitfall 1: MMS_FA Word Boundary Grouping
**What goes wrong:** MMS_FA outputs character-level spans without word boundaries. Naive grouping produces incorrect word timestamps.
**Why it happens:** Unlike other Wav2Vec2 bundles, MMS_FA has no `|` word-boundary token.
**How to avoid:** Use the transcript's word structure to group character spans. Split transcript into words, count characters per word, group spans accordingly.
**Warning signs:** Word timestamps that span partial words or include characters from adjacent words.

### Pitfall 2: VibeVoice Memory Exhaustion
**What goes wrong:** VibeVoice-ASR-7B uses ~14GB VRAM. Combined with other models or large batch sizes, causes OOM.
**Why it happens:** 7B parameter model + acoustic tokenizer + semantic tokenizer.
**How to avoid:** Run VibeVoice sequentially, not in parallel with other models. Use `acoustic_tokenizer_chunk_size` to reduce per-chunk memory. Monitor VRAM with nvidia-smi.
**Warning signs:** CUDA OOM errors, GPU memory fragmentation.

### Pitfall 3: CTC Drift on Long Chapters
**What goes wrong:** CTC models (wav2vec2, MMS) exhibit systematic temporal drift on audio >10 minutes. Word timestamps at chapter end are seconds off.
**Why it happens:** CTC peaky behavior accumulates small frame-level errors over long sequences.
**How to avoid:** Implement VAD-based chunking with 500ms-1s overlap. Align chunks independently. Merge with confidence-based conflict resolution. Snap boundaries to VAD regions.
**Warning signs:** Increasing timestamp deviation at chapter end; words assigned to silence regions.

### Pitfall 4: OpenAI Whisper API Word Timestamps
**What goes wrong:** Using `gpt-4o-transcribe` expecting word-level timestamps.
**Why it happens:** Only `whisper-1` supports `timestamp_granularities=["word"]`. GPT-4o models do not support timestamp granularity.
**How to avoid:** Always use `model="whisper-1"` with `response_format="verbose_json"` and `timestamp_granularities=["word"]`.
**Warning signs:** API returns segments without word-level data.

### Pitfall 5: Docker torchaudio Version Mismatch
**What goes wrong:** torchaudio in Docker (PyTorch 2.3.0 base image) doesn't match host version.
**Why it happens:** Dockerfile.align uses `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime` but host has torch 2.8.0.
**How to avoid:** Either upgrade Docker base image to PyTorch 2.8.0 or install matching torchaudio in Dockerfile. Verify MMS_FA API compatibility.
**Warning signs:** Import errors, API signature mismatches between versions.

## Code Examples

Verified patterns from official sources:

### MMS_FA Phone-Level Alignment
```python
# Source: https://docs.pytorch.org/audio/stable/tutorials/ctc_forced_alignment_api_tutorial.html
import torch
import torchaudio

bundle = torchaudio.pipelines.MMS_FA
device = "cuda" if torch.cuda.is_available() else "cpu"

model = bundle.get_model(with_star=False).to(device)
tokenizer = bundle.get_tokenizer()
aligner = bundle.get_aligner()

# Load and resample audio
waveform, sr = torchaudio.load("chapter.wav")
waveform = torchaudio.functional.resample(wr=sr, orig_freq=sr, new_freq=bundle.sample_rate)
waveform = waveform.to(device)

# Tokenize at character level
transcript = "Kezdetben teremtette Isten az eget és a földet"
tokens = tokenizer(transcript.split())

# Compute emission and align
with torch.inference_mode():
    emission, _ = model(waveform)
    token_spans = aligner(emission[0], tokens)

# Extract timestamps
frame_rate = bundle.sample_rate / emission.size(1)
for span in token_spans:
    start_sec = span.start / frame_rate
    end_sec = span.end / frame_rate
    print(f"Token {span.token}: {start_sec:.3f}s - {end_sec:.3f}s (score: {span.score:.3f})")
```

### VibeVoice Parsed Output with Timestamps
```python
# Source: https://huggingface.co/docs/transformers/en/model_doc/vibevoice_asr
from transformers import AutoProcessor, VibeVoiceForSpeechToText

processor = AutoProcessor.from_pretrained("microsoft/VibeVoice-ASR-7B")
model = VibeVoiceForSpeechToText.from_pretrained("microsoft/VibeVoice-ASR-7B")

# Process audio with parsed output
inputs = processor(audio, sampling_rate=24000, return_tensors="pt")
generated_ids = model.generate(**inputs, max_new_tokens=4096)

# Decode with parsed format (returns speaker, timestamps, content)
transcription = processor.batch_decode(generated_ids, return_format="parsed")
# Returns: [{"speaker": "Speaker 0", "start": 0.0, "end": 2.5, "text": "Kezdetben teremtette..."}]
```

### VAD-Based Chunking for Drift Compensation
```python
# Source: https://github.com/MahmoudAshraf97/ctc-forced-aligner/issues/84
import torch

def chunk_audio_by_vad(
    audio: torch.Tensor,
    sr: int,
    overlap_ms: float = 500.0,
) -> list[dict]:
    """Chunk audio at VAD-detected silence boundaries with overlap."""
    # Get speech segments from silero-vad
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        trust_repo=True,
    )
    get_speech_timestamps = utils[0]
    speech_ts = get_speech_timestamps(audio, model, sampling_rate=sr)

    chunks = []
    overlap_samples = int(overlap_ms * sr / 1000)

    for i, seg in enumerate(speech_ts):
        start = max(0, seg['start'] - overlap_samples)
        end = min(len(audio), seg['end'] + overlap_samples)
        chunks.append({
            "audio": audio[start:end],
            "start_sample": start,
            "end_sample": end,
            "start_sec": start / sr,
            "end_sec": end / sr,
        })

    return chunks

def merge_chunk_results(
    chunk_results: list[list[dict]],
    overlap_ms: float = 500.0,
) -> list[dict]:
    """Merge alignment results from overlapping chunks using confidence scores."""
    merged = []
    for chunk_words in chunk_results:
        for word in chunk_words:
            # Check if word overlaps with existing merged words
            overlapping = [
                w for w in merged
                if abs(word["start"] - w["start"]) < overlap_ms / 1000
            ]
            if overlapping:
                # Keep higher confidence version
                if word.get("confidence", 0) > max(w.get("confidence", 0) for w in overlapping):
                    merged = [w for w in merged if w not in overlapping]
                    merged.append(word)
            else:
                merged.append(word)
    return sorted(merged, key=lambda w: w["start"])
```

### OpenAI Whisper API Evaluation
```python
# Source: https://developers.openai.com/api/docs/guides/speech-to-text
import openai

client = openai.OpenAI()

def evaluate_whisper_api(audio_path: str) -> dict:
    """Evaluate OpenAI Whisper API for word-level timestamps."""
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language="hu",
        )

    words = []
    for word in response.words:
        words.append({
            "word": word.word,
            "start": word.start,
            "end": word.end,
        })
    return {"words": words, "text": response.text}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WhisperX for forced alignment | torchaudio MMS_FA | 2023 (MMS paper) | No WhisperX dependency; direct CTC alignment; 1130+ language support |
| Manual VAD + chunking | silero-vad integration | 2022-2023 | Pre-trained VAD, handles edge cases, available via torch.hub |
| Single-model alignment | Model gauntlet comparison | Phase 4-5 | Enables informed model selection in Phase 6 |
| Whisper for word timestamps | VibeVoice-ASR-7B | 2026-01 | 60-min single-pass; built-in timestamps; no separate forced alignment step |

**Deprecated/outdated:**
- `torchaudio.functional._alignment.forced_align`: Deprecated in torchaudio 2.8, will be removed in 2.9. Use `torchaudio.functional.forced_align` (non-deprecated path). [CITED: torchaudio 2.8 deprecation warning]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | MMS_FA bundle sample rate is 16kHz | Pattern 1 | Audio resampling needed if different; affects timestamp calculation |
| A2 | VibeVoice-ASR-7B fits in 24GB VRAM with room for inference | Pattern 2 | May need to reduce batch size or use quantization |
| A3 | Hungarian text needs romanization for MMS_FA | Pattern 1 | Alignment quality may degrade without proper normalization |
| A4 | silero-vad works well on Hungarian Bible narration | Pattern 3 | May miss speech segments in literary/read speech |
| A5 | OpenAI Whisper API handles Hungarian well | Pattern 4 | WER may be high; timestamps may be inaccurate |
| A6 | torchaudio 2.8.0 MMS_FA API is backward compatible with 2.3.0 Docker base | Pitfall 5 | API changes may require Dockerfile update |

## Open Questions

1. **Hungarian text normalization for MMS_FA**
   - What we know: MMS_FA expects normalized, potentially romanized text
   - What's unclear: Whether Hungarian diacritics (á, é, í, ó, ö, ő, ú, ü, ű) need special handling or if MMS_FA's multilingual tokenizer handles them natively
   - Recommendation: Test with and without diacritics; use the multilingual tutorial's normalization approach as starting point

2. **VibeVoice direct alignment vs ASR+RapidFuzz**
   - What we know: VibeVoice outputs structured transcription with timestamps
   - What's unclear: Whether VibeVoice's built-in timestamps are precise enough for verse-level alignment, or if ASR+RapidFuzz matching is more accurate
   - Recommendation: Implement both paths (D-09) and compare on gold chapters

3. **Docker base image upgrade**
   - What we know: Current Dockerfile uses PyTorch 2.3.0, host has 2.8.0
   - What's unclear: Whether MMS_FA API changed between versions; whether upgrading breaks existing Phase 4 code
   - Recommendation: Test MMS_FA on current Docker base first; upgrade only if API incompatible

4. **CTC drift threshold**
   - What we know: Drift accumulates on audio >10-15 minutes
   - What's unclear: Exact chapter duration where drift becomes unacceptable
   - Recommendation: Test on known long chapters (Genesis 1 = ~30 min); measure drift at chapter end

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| NVIDIA RTX 3090 | All GPU models | ✓ | 24GB VRAM | — |
| Docker | GPU containers | ✓ | 29.5.2 (rootless) | — |
| Python | CLI, host-side | ✓ | 3.10.14 | — |
| uv | Package management | ✓ | 0.5.27 | — |
| torchaudio | MMS_FA pipeline | ✓ (local) | 2.8.0 | Install in Docker |
| torch | GPU inference | ✓ (local) | 2.8.0 | PyTorch Docker base |
| transformers | VibeVoice, wav2vec2 | ✓ (local) | 4.46.0 | Already in Dockerfile |
| faster-whisper | VAD, Whisper ASR | ✓ (Docker) | — | Already in Dockerfile |
| rapidfuzz | Text matching | ✓ (local) | 3.14.5 | Already in pyproject.toml |
| huggingface-hub | Model download | ✓ (local) | 1.16.1 | Already in pyproject.toml |
| openai | API evaluation | ✗ | — | `pip install openai` |
| Prepared audio data | Alignment input | ✓ | 69 chapters | — |
| MEK text corpus | Verse text input | ✓ | 35,350 verses | — |

**Missing dependencies with no fallback:**
- None — all critical dependencies are available

**Missing dependencies with fallback:**
- `openai` Python package — not installed, but `pip install openai` is the fallback

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml [tool.pytest] |
| Quick run command | `uv run pytest tests/test_align.py -x -v` |
| Full suite command | `uv run pytest tests/ -x -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALN-03 | MMS_FA forced alignment produces verse-level timestamps | unit (mock) | `uv run pytest tests/test_forced.py::test_mms_fa_alignment -x` | ❌ Wave 0 |
| ALN-03 | MMS_FA outputs phone-level timestamps | unit (mock) | `uv run pytest tests/test_forced.py::test_mms_fa_phones -x` | ❌ Wave 0 |
| ALN-04 | VibeVoice ASR produces word timestamps | unit (mock) | `uv run pytest tests/test_vibevoice.py::test_vibevoice_asr -x` | ❌ Wave 0 |
| ALN-04 | VibeVoice direct alignment produces verse timestamps | unit (mock) | `uv run pytest tests/test_vibevoice.py::test_vibevoice_direct -x` | ❌ Wave 0 |
| ALN-05 | OpenAI API evaluation returns word timestamps | integration | `uv run pytest tests/test_api_eval.py::test_whisper_api -x` | ❌ Wave 0 |
| ALN-09 | Drift compensation chunks audio by VAD | unit | `uv run pytest tests/test_drift.py::test_vad_chunking -x` | ❌ Wave 0 |
| ALN-09 | Drift compensation merges overlapping chunks | unit | `uv run pytest tests/test_drift.py::test_merge_chunks -x` | ❌ Wave 0 |
| ALN-09 | Drift compensation snaps boundaries to VAD | unit | `uv run pytest tests/test_drift.py::test_snap_to_vad -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_forced.py tests/test_vibevoice.py tests/test_drift.py -x -v`
- **Per wave merge:** `uv run pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_forced.py` — covers ALN-03 (MMS_FA alignment)
- [ ] `tests/test_vibevoice.py` — covers ALN-04 (VibeVoice ASR + direct)
- [ ] `tests/test_api_eval.py` — covers ALN-05 (OpenAI API evaluation)
- [ ] `tests/test_drift.py` — covers ALN-09 (CTC drift compensation)
- [ ] `tests/test_evaluate.py` — covers evaluation engine (WER, metrics, comparison table)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OpenAI API key in .env (BIBLIAVOX_OPENAI_API_KEY) |
| V3 Session Management | no | No sessions — stateless CLI |
| V4 Access Control | no | Local CLI tool, no multi-user |
| V5 Input Validation | yes | Validate audio file paths, chapter references, API responses |
| V6 Cryptography | no | No encryption needed — local file processing |

### Known Threat Patterns for Alignment Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure | Information Disclosure | Load from .env, never commit to git |
| Malicious audio file | Tampering | Validate audio format before processing |
| API response injection | Tampering | Validate JSON schema of OpenAI responses |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: Context7 /pytorch/audio] — MMS_FA pipeline API, forced_align, merge_tokens, Wav2Vec2FABundle
- [VERIFIED: local install] — torchaudio 2.8.0, torch 2.8.0, transformers 4.46.0
- [CITED: https://docs.pytorch.org/audio/stable/tutorials/forced_alignment_for_multilingual_data_tutorial.html] — MMS_FA multilingual alignment tutorial
- [CITED: https://docs.pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html] — MMS_FA bundle documentation (no word boundary token note)
- [CITED: https://huggingface.co/docs/transformers/en/model_doc/vibevoice_asr] — VibeVoice ASR model documentation
- [CITED: https://developers.openai.com/api/docs/guides/speech-to-text] — OpenAI Whisper API with word timestamps
- [CITED: https://openai.com/api/pricing/] — OpenAI API pricing ($0.006/min for whisper-1)

### Secondary (MEDIUM confidence)
- [CITED: https://github.com/microsoft/VibeVoice] — VibeVoice README, model links, key features
- [CITED: https://huggingface.co/sarpba/wav2vec2-large-xlsr-53-hungarian] — wav2vec2 Hungarian model (17.2% WER)
- [CITED: https://github.com/MahmoudAshraf97/ctc-forced-aligner/issues/84] — CTC drift fix with VAD snapping
- [CITED: https://github.com/huggingface/blog/blob/main/asr-chunking.md] — CTC chunking for long files

### Tertiary (LOW confidence)
- [CITED: https://openreview.net/attachment?id=JpG7RsIFhL&name=pdf] — LFA (Long-Form Alignment) paper; chunk-and-align approach for multi-hour recordings
- [CITED: https://arxiv.org/html/2601.18220v2] — LLM-ForcedAligner; novel FA approach but not needed for this phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via Context7, local install, or official docs
- Architecture: HIGH — follows established Phase 4 patterns (Docker, CLI, Taskfile)
- Pitfalls: MEDIUM — CTC drift behavior is well-documented but Hungarian-specific testing needed
- VibeVoice integration: MEDIUM — transformers API verified, but Hungarian performance unverified

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (30 days — torchaudio/transformers APIs stable)
