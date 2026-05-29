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
bibliavox/
├── src/                    # Python package source
├── tests/                  # Test suite
├── docker/                 # Dockerfiles for model stages
├── data/                   # Downloaded text/audio (not versioned)
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

- **Phase:** 1 of 8 (Foundation & Versification Schema)
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

- **Text (primary):** szentiras.eu API (SZIT translation) — needs API key
- **Text (fallback):** mek.oszk.hu HTML scraping
- **Audio:** mek.oszk.hu per-chapter MP3s (Szent István Társulat)

## Key Decisions

- Start with Szent István Társulat only (same translation for text and audio)
- Transcribe-then-match architecture (faster-whisper + RapidFuzz)
- torchaudio MMS_FA as secondary forced alignment tier
- Docker for model-heavy stages only, native Python for lightweight stages
- Each phase delivers working Typer commands and Taskfile targets

## Known Blockers

- szentiras.eu API key requires emailing maintainers
- mek.oszk.hu audio completeness for all 73 Catholic books unverified
- Hungarian Whisper LoRA performance on Bible narration unverified
