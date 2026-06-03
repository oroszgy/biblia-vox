# AGENTS.md — BibliaVox

## Project Overview

A CLI workflow (Taskfile + Python/uv/typer) that maps Hungarian Catholic Bible verses (Szent István Társulat translation) to audio file timestamps. The output is a JSONL of verse-to-audio mappings with metadata.

**Core Value:** Every verse of the Szent István Társulat Bible can be located in its audio recording — with precise timestamps and confidence metadata.

**v1 Scope:** Calibration release — build the full pipeline, validate on a gold subset of chapters, explore alignment approaches, prove the architecture.

## Tech Stack

- **Language:** Python 3.13+
- **Package Manager:** uv
- **CLI Framework:** typer
- **Linting/Type Checking:** ruff, ty
- **Workflow:** Taskfile (go-task)
- **Infrastructure:** Docker + docker-compose (for GPU model stages), native Python (for lightweight stages)
- **GPU:** NVIDIA RTX 3090

## Project Structure

```
cath-bible-voice/
├── bibliavox/              # Python package (flat layout)
│   ├── reference/          # Bible book catalog & versification
│   │   ├── books.py        # 73-book Catholic Bible catalog
│   │   ├── schema.py       # Chapter/verse counts per book
│   │   └── generate.py     # CLI for generating reference JSON
│   ├── cli/                # CLI subcommands
│   ├── config.py           # Pydantic Settings configuration
│   └── main.py             # Typer app entry point
├── tests/                  # Test suite
├── data/                   # Reference data (not versioned)
│   └── reference/          # books.json, versification.json
├── docker/                 # Dockerfiles for model stages
├── .planning/              # GSD planning documents
├── Taskfile.yml            # Task definitions
├── docker-compose.yml      # Docker orchestration
└── pyproject.toml          # Python project config
```

## Key Commands

```bash
# Development
uv sync                     # Install dependencies
uv run bibliavox --help  # Run CLI
task --list                 # List available tasks

# Quality
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run ty check .           # Type check

# Testing
uv run pytest               # Run tests
```

## GSD Workflow

This project uses the Get Shit Done (GSD) workflow system. Planning documents are in `.planning/`.

### Current State

- **Phase:** 8 of 8 (Operations & Pipeline Hardening)
- **Status:** Ready to plan

### Workflow Commands

```bash
/gsd-plan-phase 1           # Plan the current phase
/gsd-execute-phase 1        # Execute the current phase
/gsd-verify-work 1          # Verify phase completion
/gsd-progress               # View project status
```

### Phase Execution Order

1. Foundation & Versification Schema
2. Text Acquisition & Validation (parallel with 3)
3. Audio Pipeline (parallel with 2)
4. Transcription-Based Alignment (includes Docker setup)
5. Forced Alignment & Alternatives
6. Calibration & Alignment Comparison
7. Export & Pipeline Integration
8. Operations & Pipeline Hardening

## Data Sources

- **Text (primary):** mek.oszk.hu HTML scraping (all 73 Catholic books)
- **Text (experimental):** peterpolgar/Biblia-json-xml (SZIT translation, 66 books only)
- **Audio:** mek.oszk.hu per-chapter MP3s (Szent István Társulat)

## Alignment Models

| Model | Type | Status |
|-------|------|--------|
| `microsoft/VibeVoice-ASR-HF` | ASR + RapidFuzz | Working (best WER: 0.69) |
| `systran/faster-whisper-large-v3` | Whisper | Working (WER: 0.72) |
| `sarpba/wav2vec2-large-xlsr-53-hungarian` | CTC | Working (WER: 0.86, fastest) |

## Key Decisions

- MEK as primary text source (covers all 73 Catholic books)
- SZIT text pipeline kept as experimental (only 66 books)
- Transcribe-then-match architecture (ASR + RapidFuzz)
- Docker for model-heavy stages only, native Python for lightweight stages
- Each phase delivers working Typer commands and Taskfile targets

## Known Blockers

- mek.oszk.hu audio completeness for all 73 Catholic books unverified
- Hungarian Whisper LoRA performance on Bible narration unverified
