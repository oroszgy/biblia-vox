# Technology Stack

**Project:** bibliavox
**Researched:** 2026-05-28
**Overall confidence:** HIGH (core stack), MEDIUM (alignment model selection)

## Recommended Stack

### Core Framework (Already Decided)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | >=3.13 | Runtime | Project constraint, already set in pyproject.toml |
| uv | latest | Package manager | Project constraint, fast, pyproject.toml-native |
| typer | >=0.26 | CLI framework | Project constraint, type-hint-based, Rich integration |
| ruff | latest | Linter/formatter | Project constraint |
| ty | latest | Type checker | Project constraint |
| Taskfile (go-task) | latest | Task orchestration | Project constraint, granular task definitions |

### Speech Recognition (Transcription)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| faster-whisper | >=1.2.1 | Speech-to-text engine | 4x faster than OpenAI Whisper at same accuracy, CTranslate2 backend, int8 quantization, word_timestamps support, MIT license | HIGH |
| Maxdorger29/whisper-large-v3-turbo-hungarian-lora | latest | Hungarian Whisper model | LoRA fine-tuned for Hungarian, fixes hallucinations on Hungarian characters/names, CTranslate2-compatible, ~1.6GB VRAM | MEDIUM |

**Why faster-whisper over OpenAI Whisper:**
- 4x faster at same accuracy (1m03s vs 2m23s for large-v2 on GPU)
- Batched inference: 16x faster (17s vs 2m23s)
- int8 quantization: 50% less VRAM (2926MB vs 4708MB)
- Native word_timestamps via cross-attention + DTW
- VAD filter built-in (Silero VAD v5)
- MIT license (OpenAI Whisper is also MIT, but faster-whisper is strictly better)

**Why Hungarian LoRA over base Whisper:**
- Base Whisper hallucinates on Hungarian special characters (á, é, í, ó, ö, ő, ú, ü, ű)
- Hallucinates words during silence segments
- LoRA fine-tuned on Hungarian data, CTranslate2 quantized
- Fits on 3090 easily (~1.6GB VRAM for turbo model)

**Why NOT openai/whisper directly:**
- Slower, no batched inference, no int8 quantization
- Word timestamps less accurate than faster-whisper's implementation

### Forced Alignment (Word-Level Timestamps)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| torchaudio | >=2.8 | Forced alignment API | `MMS_FA` bundle: multilingual wav2vec2 model covering 1130 languages including Hungarian, `forced_align()` CUDA implementation, simple API | HIGH |
| transformers (HuggingFace) | >=4.33 | wav2vec2 model loading | Load `sarpba/wav2vec2-large-xlsr-53-hungarian` (17% WER vs 46% for jonatasgrosman model) | MEDIUM |

**Recommended two-tier alignment strategy:**

1. **Primary: faster-whisper word_timestamps** — built-in, no extra model needed, uses cross-attention patterns + DTW. Sufficient for verse-level matching when combined with fuzzy text matching.

2. **Secondary (if needed): torchaudio MMS_FA** — for sub-word precision. The MMS model was trained on 31K hours across 1130 languages. Hungarian is covered. Use `torchaudio.functional.forced_align()` with CUDA for best performance.

3. **Fallback: custom wav2vec2** — `sarpba/wav2vec2-large-xlsr-53-hungarian` (17% WER on CV17) via HuggingFace transformers + custom CTC alignment. Only if MMS_FA quality is insufficient.

**Why torchaudio MMS_FA over WhisperX:**
- WhisperX had a critical word-timestamp bug from v3.3.3 to v3.8.1 (PR #1367, fixed March 2026). The fix reverts to the PyTorch tutorial approach — which torchaudio already provides natively.
- WhisperX's default Hungarian model (`jonatasgrosman/wav2vec2-large-xlsr-53-hungarian`) has 46% WER — significantly worse than alternatives.
- WhisperX adds complexity (pyannote, NLTK) we don't need (no diarization, no sentence splitting).
- torchaudio's `forced_align()` has custom CPU and CUDA implementations that are more performant.

**Why NOT Montreal Forced Aligner (MFA):**
- Requires conda installation (incompatible with uv-based workflow)
- Kaldi-based: complex dependency chain, slow to install
- Hungarian model trained on only 16 hours of Common Voice data
- GMM-HMM architecture is older than wav2vec2 CTC approaches
- Output format (TextGrid) requires additional parsing

**Note on torchaudio maintenance mode:** TorchAudio 2.8+ entered maintenance mode, but `forced_align()` is explicitly preserved (confirmed in v2.10 release notes). The API is stable and will not be removed.

### Audio Processing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pydub | >=0.25.1 | High-level audio manipulation | Simple API for MP3 loading, slicing, format conversion via ffmpeg. Stable, well-known. | HIGH |
| soundfile | >=0.13.1 | Low-level audio I/O | Fast numpy array I/O via libsndfile, preserves original sample rate, needed for ML pipeline | HIGH |
| ffmpeg | system | Audio codec backend | Required by pydub, handles MP3 decoding. System dependency. | HIGH |

**Why pydub + soundfile (not one or the other):**
- pydub: High-level operations (load MP3, slice by milliseconds, export). Perfect for "load chapter MP3, extract verse segments."
- soundfile: Low-level numpy array I/O at native sample rate. Required for feeding audio to ML models (wav2vec2 expects 16kHz float32 arrays).
- librosa: NOT recommended as primary — auto-resamples to 22050Hz by default (surprising behavior), heavy dependency tree. Use only if specific audio features (spectrograms, etc.) are needed later.

**Why NOT torchaudio for audio I/O:**
- Entering maintenance mode
- Returns PyTorch tensors (extra conversion step for non-ML code)
- soundfile is simpler for pure I/O

### Text Processing & Fuzzy Matching

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| rapidfuzz | >=3.14 | Fuzzy string matching | C++ backed, MIT licensed, 40% faster than alternatives, drop-in replacement for thefuzz | HIGH |
| unicodedata (stdlib) | — | Unicode normalization | Hungarian text normalization (NFC/NFD), accent handling | HIGH |
| re (stdlib) | — | Text normalization | Strip punctuation, normalize whitespace before matching | HIGH |

**Why RapidFuzz over TheFuzz:**
- C++ implementation: orders of magnitude faster
- MIT license (TheFuzz is MIT too, but RapidFuzz is strictly faster)
- More algorithms: Levenshtein, Jaro-Winkler, Hamming, etc.
- `process.cdist()` for batch comparison with multi-core support
- TheFuzz actually uses RapidFuzz as its backend since v0.20

**Why NOT difflib (stdlib):**
- Slower, less accurate for non-English text
- No C++ acceleration
- Limited algorithm choices

### Data Pipeline & Serialization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| json (stdlib) | — | JSONL output | Project requires JSONL format, stdlib is sufficient | HIGH |
| httpx | >=0.28 | HTTP client | For szentiras.eu API calls, async support, modern API | HIGH |
| beautifulsoup4 | >=4.12 | HTML parsing | For mek.oszk.hu fallback scraping | MEDIUM |
| lxml | >=5.0 | HTML/XML parser backend | Fast parser for beautifulsoup4 | MEDIUM |

**Why httpx over requests:**
- Async support (useful for parallel API calls)
- HTTP/2 support
- Modern API design
- Same simplicity as requests

### GPU & ML Infrastructure

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| torch (PyTorch) | >=2.5 | ML framework | Required by faster-whisper, torchaudio, transformers | HIGH |
| ctranslate2 | >=4.5 | Inference engine | Backend for faster-whisper, CUDA 12 + cuDNN 9 support | HIGH |
| huggingface-hub | >=0.26 | Model downloads | Download Whisper models, wav2vec2 models | HIGH |

**GPU utilization on RTX 3090 (24GB VRAM):**
- faster-whisper large-v3-turbo (fp16): ~6GB VRAM
- faster-whisper large-v3-turbo (int8): ~3GB VRAM
- wav2vec2-large-xlsr-53: ~1.5GB VRAM
- Total pipeline: ~8-10GB VRAM (well within 3090 capacity)
- Can run transcription and alignment sequentially on same GPU

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Transcription | faster-whisper | openai/whisper | 4x slower, no batching, no quantization |
| Transcription | faster-whisper | whisper.cpp (via pywhispercpp) | C++ binary, harder to integrate, no Python-native word timestamps |
| Transcription | faster-whisper | WhisperX | Unnecessary complexity (diarization, NLTK), had critical alignment bug v3.3.3-v3.8.1 |
| Alignment | torchaudio MMS_FA | Montreal Forced Aligner | Requires conda, Kaldi dependency, incompatible with uv workflow |
| Alignment | torchaudio MMS_FA | WhisperX alignment | Default Hungarian model has 46% WER, dependency on torchaudio anyway |
| Alignment | torchaudio MMS_FA | Gentle | Kaldi-based, complex installation, outdated |
| Audio I/O | pydub + soundfile | librosa only | Auto-resamples to 22050Hz, heavy dependencies |
| Audio I/O | pydub + soundfile | torchaudio only | Maintenance mode, PyTorch tensors for simple I/O |
| Fuzzy matching | rapidfuzz | thefuzz | thefuzz uses rapidfuzz as backend anyway, slower API |
| Fuzzy matching | rapidfuzz | difflib (stdlib) | Slower, fewer algorithms, no C++ acceleration |
| HTTP client | httpx | requests | No async, no HTTP/2 |
| Hungarian model | Maxdorger29 LoRA | sarpba/whisper-hu-large-v3-turbo-finetuned | Both viable; Maxdorger29 is CTranslate2-native, sarpba is transformers-native |
| wav2vec2 model | sarpba/wav2vec2-large-xlsr-53-hungarian | jonatasgrosman/wav2vec2-large-xlsr-53-hungarian | jonatasgrosman has 46% WER vs sarpba's 17% on CV17 |

## Installation

```bash
# Core dependencies
uv add typer rich httpx pydub soundfile rapidfuzz beautifulsoup4 lxml

# ML dependencies (GPU)
uv add torch torchaudio --index-url https://download.pytorch.org/whl/cu124
uv add faster-whisper huggingface-hub

# Dev dependencies
uv add --dev ruff ty pytest
```

**System dependencies:**
```bash
# ffmpeg (required by pydub)
sudo apt install ffmpeg

# CUDA 12 + cuDNN 9 (for GPU acceleration)
# Assumes NVIDIA driver already installed
```

## Dependency Graph

```
CLI Layer:        typer + rich
                  ↓
Orchestration:    Taskfile (go-task)
                  ↓
Pipeline:         download → parse → transcribe → align → match → export
                  ↓           ↓       ↓            ↓       ↓        ↓
I/O:             httpx    bs4+lxml  faster-     torch-  rapid-   json
                 (API)    (HTML)    whisper     audio   fuzz     (JSONL)
                                     ↓           ↓
                  Models:     Hungarian LoRA   MMS_FA / wav2vec2
                  Audio:      pydub + soundfile + ffmpeg
                  GPU:        torch + ctranslate2 + CUDA 12
```

## Key Architectural Decision: Transcribe-then-Match

The recommended pipeline is:

1. **Transcribe** each chapter MP3 with faster-whisper (Hungarian LoRA) → segments with word timestamps
2. **Normalize** both transcribed text and Bible verse text (lowercase, strip punctuation, NFC normalize)
3. **Sliding window match**: For each verse, find the best matching window of consecutive words in the transcription using RapidFuzz
4. **Refine timestamps**: Use the word-level timestamps from the matched window as verse start/end
5. **Score confidence**: Based on fuzzy match ratio + word probability scores from Whisper

This is preferred over forced-alignment-with-known-text because:
- We don't need a pronunciation dictionary for Hungarian Bible vocabulary
- Whisper handles the speech-to-text step, avoiding the need for phoneme-level accuracy
- Fuzzy matching handles minor transcription errors gracefully
- The pipeline is simpler and more debuggable

**When to add forced alignment (tier 2):**
If fuzzy matching produces low-confidence results for specific verses, use torchaudio MMS_FA to force-align the known verse text to the audio segment identified by fuzzy matching. This two-stage approach gives both robustness and precision.

## Sources

- faster-whisper GitHub: https://github.com/SYSTRAN/faster-whisper (22K stars, MIT, v1.2.1)
- faster-whisper Context7 docs: word_timestamps, batched inference confirmed
- WhisperX alignment.py: Hungarian default model = `jonatasgrosman/wav2vec2-large-xlsr-53-hungarian`
- WhisperX PR #1367: Critical word-timestamp fix (March 2026)
- Hungarian Whisper LoRA: https://huggingface.co/Maxdorger29/whisper-large-v3-turbo-hungarian-lora
- sarpba wav2vec2 Hungarian: 17% WER vs jonatasgrosman 46% WER (CV17 benchmark)
- torchaudio MMS_FA: https://docs.pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html
- torchaudio maintenance mode: confirmed in v2.8+ release notes, forced_align preserved
- MFA Hungarian: https://mfa-models.readthedocs.io/en/latest/acoustic/Hungarian/ (16h Common Voice, GMM-HMM)
- RapidFuzz: https://rapidfuzz.github.io/RapidFuzz/ (v3.14.5, MIT, C++ backend)
- RapidFuzz benchmarks: 40% faster than alternatives, O(N²) but with C++ speed
- pydub: v0.25.1 (stable, last release 2021, pydub-ng fork exists for modern Python)
- soundfile: v0.13.1 (active, libsndfile-based)
- typer: v0.26.1 (active, MIT, FastAPI sibling)
- MMS paper: Pratap et al., "Scaling Speech Technology to 1,000+ Languages" (JMLR 2024)
