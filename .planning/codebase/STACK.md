# Technology Stack

**Analysis Date:** 2026-06-02

## Languages

**Primary:**
- Python 3.13 — All application code in `bibliavox/` package (`.python-version` pinned)

**Secondary:**
- YAML — Taskfile task definitions (`Taskfile.yml`)
- Dockerfile — GPU alignment container (`docker/Dockerfile.align`)

## Runtime

**Environment:**
- Python 3.13 (pinned in `.python-version`)
- NVIDIA CUDA 12.1 + cuDNN 8 (Docker base image: `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`)

**Package Manager:**
- uv — Fast Python package installer and resolver
- Lockfile: `uv.lock` present (586 lines, deterministic dependency resolution)

## Frameworks

**Core:**
- typer >=0.26 — CLI framework with subcommand groups (`bibliavox/main.py`)
- rich — Terminal formatting, tables, progress bars (used in all CLI modules)
- pydantic-settings — Configuration via environment variables with `BIBLIAVOX_` prefix (`bibliavox/config.py`)

**Testing:**
- pytest — Test runner with coverage support
- Config: No `pytest.ini` or `pyproject.toml [tool.pytest]` section detected

**Build/Dev:**
- ruff — Linter and formatter (replaces flake8, black, isort)
- ty — Type checker (new Python type checker)
- hatchling — PEP 517 build backend (`pyproject.toml [build-system]`)

**Task Runner:**
- Taskfile (go-task) v3 — YAML-based task definitions (`Taskfile.yml`)
- 25+ tasks covering lint, format, typecheck, test, reference generation, text operations, audio operations, alignment

## Key Dependencies

**Critical:**
- `typer >=0.26` — CLI framework, entry point at `bibliavox/main.py:main()`
- `rapidfuzz >=3.14.5` — Fuzzy string matching for verse-to-transcript alignment (`bibliavox/align/match.py`)
- `httpx >=0.28` — HTTP client for MEK text/audio downloads with retry support
- `beautifulsoup4 >=4.14.3` — HTML parsing for MEK text source (`bibliavox/text/mek_source.py`)

**Infrastructure:**
- `tenacity >=9.1` — Retry logic with exponential backoff for HTTP requests
- `huggingface-hub >=1.16.1` — Model weight downloading for alignment models
- `pydantic-settings` — Environment-based configuration management

**Dev Dependencies:**
- `ruff` — Linting and formatting
- `pytest` — Testing framework

## Docker Configuration

**Alignment Container:**
- Base: `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`
- Dockerfile: `docker/Dockerfile.align`
- Compose: `docker-compose.yml` with NVIDIA GPU passthrough
- Installed packages: faster-whisper, rapidfuzz, torchaudio, transformers, accelerate, librosa, soundfile
- System deps: ffmpeg, git, libsndfile1

**GPU Requirements:**
- NVIDIA GPU with CUDA support (RTX 3090 mentioned in AGENTS.md)
- Docker Compose reserves all available GPUs: `capabilities: [gpu]`
- Model inference uses `device="cuda"` with `compute_type="float16"` (`bibliavox/align/transcribe.py:37`)

## Configuration

**Environment:**
- All settings use `BIBLIAVOX_` prefix via pydantic-settings
- `.env` file support (gitignored)
- Key settings: `BIBLIAVOX_DATA_DIR`, `BIBLIAVOX_CACHE_DIR`, `BIBLIAVOX_REFERENCE_DATA_PATH`, `BIBLIAVOX_SZENTIRAS_API_KEY`
- Singleton pattern with `get_settings()` / `reset_settings()` (`bibliavox/config.py:84-103`)

**Build:**
- `pyproject.toml` — Project metadata, dependencies, entry point
- `Taskfile.yml` — Task definitions (lint, format, typecheck, test, reference, text, audio, align)
- `docker-compose.yml` — GPU alignment service

## Platform Requirements

**Development:**
- Python 3.13+
- uv package manager
- go-task (Taskfile runner)
- ffmpeg/ffprobe (audio conversion and metadata)
- Git

**Production:**
- Docker with NVIDIA GPU support (for alignment/transcription)
- Native Python (for lightweight text/reference/audio tasks)
- ffmpeg/ffprobe available on PATH

---

*Stack analysis: 2026-06-02*
