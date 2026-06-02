# Phase 4 Technical Research

## Architecture

1. **Dockerized Alignment Services**: The Python app (host) invokes Docker containers to execute model inference via `docker-compose run`. The containers share `./data` volume.
2. **Model Gauntlet**: `config.py` contains a list of models to evaluate. The script dynamically loads them.
3. **Fuzzy Matching**: Word-level RapidFuzz against transcriptions.

## Dependencies
- `faster-whisper`
- `rapidfuzz`

---

## Model Research (RTX 3090, 24GB VRAM)

### The "HuBERT" Name Clash

The model `SZTAKI-HLT/hubert-base-cc` (referenced in config as `hubert-base-cc-hu`) is a Hungarian **text** BERT model ("huBERT" = **Hu**ngarian **BERT**), NOT an audio/speech model. It is a RoBERTa-based text model pre-trained on the Hungarian Webcorpus for NLP tasks like NER and chunking. It will crash the audio transcription pipeline because it expects text tokens, not audio waveforms. It must be removed from the gauntlet.

### Recommended Model Selection

| Model HF ID | Role | Approx. VRAM | License | Hungarian Suitability |
|---|---|---|---|---|
| `systran/faster-whisper-large-v3` | ASR Transcription | 4.5 GB | Apache 2.0 | Excellent. Leading multilingual ASR with word-level timestamps and robust VAD. |
| `bofenghuang/whisper-large-v2-cv11-hu` | ASR Transcription | 6.0 GB | Apache 2.0 | High. Fine-tuned on Hungarian Common Voice. Gated fallback to `large-v2`. |
| `facebook/mms-1b-fl102` | Forced Alignment | 2.2 GB | CC-BY-NC 4.0 | Superior. Meta's MMS trellis-based word-to-audio matching. |
| `sarpba/wav2vec2-large-xlsr-53-hungarian` | CTC Alignment | 1.5 GB | Apache 2.0 | High. 17.2% WER on Common Voice 17.0 Hungarian test set. |
| `jonatasgrosman/wav2vec2-large-xlsr-53-hungarian` | CTC Alignment | 1.5 GB | Apache 2.0 | High. 31.4% WER, well-documented. |

### Microsoft VibeVoice Analysis

- **Model**: `VibeVoice-ASR-7B`
- **Architecture**: Integrates a speech encoder with a 7B parameter Qwen LLM decoder.
- **Key Features**: Long-form audio transcription (60 min), joint ASR+diarization+timestamping, over 50 languages including Hungarian (`hu`).
- **VRAM**: ~14GB in FP16. Runs comfortably on RTX 3090.
- **License**: MIT.
- **Recommendation**: Excellent as a premium ASR transcriber. Use CTC/MMS models for precision-level frame boundaries.

### Recommended Pipeline Strategy

1. **Primary ASR**: `faster-whisper-large-v3` or `VibeVoice-ASR-7B` for high-quality transcription.
2. **Forced Alignment**: `facebook/mms-1b-fl102` or `wav2vec2-large-xlsr-53-hungarian` for sub-word precision mapping.
