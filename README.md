# BibliaVox

Hungarian Catholic Bible verse-to-audio alignment tool. Maps every verse of the Szent István Társulat Bible to precise timestamps in per-chapter audio recordings.

## Project Goals

BibliaVox solves a specific problem: locating any verse of the Hungarian Catholic Bible (Szent István Társulat translation) within audio recordings. The pipeline:

1. **Acquires text** from MEK HTML (primary, all 73 Catholic books)
2. **Downloads and prepares audio** from mek.oszk.hu per-chapter MP3 recordings
3. **Aligns text to audio** using speech recognition models (VibeVoice, faster-whisper, wav2vec2 CTC)
4. **Exports JSONL** with precise timestamps, confidence scores, and text matching metrics

**Core value:** Every verse can be located in its audio recording — with timestamps and quality metadata.

## Architecture

```mermaid
graph TB
    subgraph "Shared Setup"
        T1[/"mek.oszk.hu HTML"/] -->|text:ingest-mek| T2([mek.jsonl])
        A1[/"mek.oszk.hu MP3s"/] -->|audio:download-all| A2([Raw MP3s])
        A2 -->|audio:prepare-all| A3([16kHz WAV])
    end

    T2 -->|export:align| X1
    A3 -->|export:align| X1
    T2 -->|align:evaluate-gold| E1
    A3 -->|align:evaluate-gold| E1

    subgraph EVAL["1. Evaluate"]
        E1([Evaluation Summary<br/><i>WER · CER · Confidence</i>])
    end

    subgraph EXPORT["2. Export"]
        X1([Matched verses])
        X1 -->|export:jsonl| X2([Verse-to-Audio JSONL])
    end

    style T1 fill:#e1f5fe
    style A1 fill:#e1f5fe
    style E1 fill:#fff3e0
    style X2 fill:#c8e6c9
```

## Use Cases

### 1. Evaluate a Model

Compare alignment models on a small set of "gold" chapters to check quality before committing to a full run.

```bash
# Install dependencies
uv sync

# Pre-download model weights
go-task align:setup

# Run ALL gauntlet models on 10 gold chapters (no MODEL= specified)
go-task align:evaluate-gold

# Or run a single model
go-task align:evaluate-gold MODEL=microsoft/VibeVoice-ASR-HF
```

Results are saved to `data/evaluation/` with WER, CER, and confidence metrics per verse.

### 2. Generate Verse-to-Audio Mappings

Run the full pipeline to produce JSONL output mapping every verse to its audio timestamp.

```bash
# Install dependencies
uv sync

# Run on gold chapters only (fast, ~30 chapters)
go-task export:run-gold

# Run on all 1175 chapters
go-task export:run

# Use a different model
go-task export:run MODEL=systran/faster-whisper-large-v3
```

Output is written to `data/export/`. See [JSONL Output Format](#jsonl-output-format) for the schema.

## Taskfile Commands

### Development

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `go-task lint` | Run ruff linter | `bibliavox/`, `tests/` | Terminal |
| `go-task format` | Auto-format code with ruff | `bibliavox/`, `tests/` | In-place |
| `go-task typecheck` | Run ty type checker | `bibliavox/` | Terminal |
| `go-task test` | Run test suite | `tests/` | Terminal |
| `go-task quality` | All checks (lint + format + typecheck + test) | `bibliavox/`, `tests/` | Terminal |

### Text Pipeline

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `go-task text:ingest-mek` | Download and parse MEK HTML text corpus | mek.oszk.hu | `data/processed/text/mek.jsonl` |
| `go-task data:coverage` | Strict coverage audit | `data/processed/text/mek.jsonl`, audio | Terminal |

### Audio Pipeline

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `go-task audio:download-all` | Download all chapter MP3s from MEK | mek.oszk.hu playlist | `data/raw/audio/{BOOK}/{CHAPTER}.mp3` |
| `go-task audio:prepare-all` | Convert MP3s to 16kHz WAV with metadata | `data/raw/audio/` | `data/prepared/audio/{BOOK}/{CHAPTER}.wav` + `.meta.json` + `.index.json` |

### Alignment Pipeline

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `go-task align:vibevoice BOOK=GEN CHAPTER=1` | Run VibeVoice on single chapter | `data/prepared/audio/{BOOK}/{CHAPTER}.wav` | `data/aligned/vibevoice/{BOOK}/{CHAPTER}.json` |
| `go-task align:evaluate-gold` | Evaluate models on 10 gold chapters | `data/prepared/audio/`, `data/processed/text/mek.jsonl` | `data/evaluation/{BOOK}_{CHAPTER}_{MODEL}_matched.json` |
| `go-task align:setup` | Pre-download model weights | HuggingFace Hub | `data/models/` |

### Export Pipeline

| Command | Description | Input | Output |
|---------|-------------|-------|--------|
| `go-task export:run` | Full pipeline on all chapters | `data/prepared/audio/`, `data/processed/text/mek.jsonl` | `data/export/*.jsonl` |
| `go-task export:run-gold` | Full pipeline on gold chapters only | Same as above (filtered) | `data/export/*_{MODEL}.jsonl` |
| `go-task export:jsonl` | Export alignment to JSONL | `data/evaluation/*_matched.json` | `data/export/{BOOK}_{CHAPTER}_{MODEL}.jsonl` |
| `go-task export:align` | Run alignment on all chapters | `data/prepared/audio/` | `data/aligned/{MODEL}/{BOOK}/{CHAPTER}.json` |

### Experimental Tasks (SZIT Source)

These tasks use the alternative SZIT text source (66 books only, vs MEK's 73 books). The main pipeline uses MEK exclusively.

| Command | Description |
|---------|-------------|
| `go-task experiment:text-fetch` | Download SZIT Bible JSON from GitHub |
| `go-task experiment:text-convert-jsonl` | Convert SZIT JSON to JSONL |
| `go-task experiment:text-fix-verses` | Fix embedded verse markers |
| `go-task experiment:text-cross-validate` | Cross-validate SZIT vs MEK corpora |
| `go-task experiment:text-validate` | Validate SZIT verse counts |
| `go-task experiment:text-normalize` | Normalize SZIT text |

### Common Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL=` | *(all gauntlet models)* | Model ID to use for alignment. Omit to run all models. |
| `GOLD=true` | — | Restrict to gold chapters (TIT 1-3, TOB 1-4, ZEP 1-3) |
| `FORCE=true` | — | Force re-run, skip cache |

## JSONL Output Format

Each line in the output JSONL contains:

```json
{
  "verse_ref": "GEN 1:1",
  "audio_file": "data/prepared/audio/GEN/001.wav",
  "start_sec": 6.195,
  "end_sec": 22.76,
  "source": "microsoft/VibeVoice-ASR-HF",
  "translation": "SZIT",
  "confidence": 0.951,
  "canonical_text": "Kezdetben teremtette Isten az eget és a földet.",
  "matched_text": "Kezdetben teremtette Isten az eget és a földet.",
  "wer": 0.0,
  "cer": 0.0
}
```

## Data Sources

| Source | Content | Coverage | Role |
|--------|---------|----------|------|
| **mek.oszk.hu** | Audio MP3s + HTML text | 73 books, 1175 chapters | Primary |
| **peterpolgar/Biblia-json-xml** | SZIT JSON (H_Kaldi_SZIT.json) | 66 books | Experimental |

## Dependencies

### Python
- **typer** — CLI framework
- **rich** — Terminal UI (progress bars, tables)
- **pydantic-settings** — Configuration management
- **httpx** — Async HTTP client
- **beautifulsoup4** — HTML parsing (MEK text extraction)
- **rapidfuzz** — Fuzzy text matching
- **huggingface-hub** — Model downloads

### External Tools
- **uv** — Python package manager
- **go-task** — Task runner
- **ffmpeg/ffprobe** — Audio conversion (via Docker)
- **Docker + NVIDIA Container Toolkit** — GPU model inference

## GPU Models

| Model | Type | Use Case |
|-------|------|----------|
| `microsoft/VibeVoice-ASR-HF` | ASR + RapidFuzz | Best quality (WER: 0.69) |
| `systran/faster-whisper-large-v3` | Whisper | General purpose (WER: 0.72) |
| `sarpba/wav2vec2-large-xlsr-53-hungarian` | CTC | Fastest (WER: 0.86) |

## Project Structure

```
bibliavox/
├── cli/           # CLI subcommands (text, audio, align, export)
├── align/         # Alignment engines (transcribe, match, evaluate)
├── export/        # JSONL export writer
└── config.py      # Pydantic Settings configuration

data/
├── raw/           # Downloaded source files
├── processed/     # Normalized text, evaluation results
├── prepared/      # Audio WAVs with metadata
├── aligned/       # Cached alignment results
└── export/        # Final JSONL output
```

## License

MIT License. See [LICENSE](LICENSE) for details.
