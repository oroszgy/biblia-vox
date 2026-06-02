# Codebase Structure

**Analysis Date:** 2026-06-02

## Directory Layout

```
cath-bible-voice/
├── bibliavox/              # Python package (flat layout, all source code)
│   ├── __init__.py         # Package marker
│   ├── main.py             # CLI entry point (Typer app registration)
│   ├── config.py           # Pydantic Settings (BIBLIAVOX_ prefix)
│   ├── coverage.py         # Dataset coverage audit engine
│   ├── cli/                # CLI subcommand groups
│   │   ├── __init__.py
│   │   ├── reference.py    # `bibliavox reference` commands
│   │   ├── text.py         # `bibliavox text` commands
│   │   ├── audio.py        # `bibliavox audio` commands
│   │   ├── data.py         # `bibliavox data` commands
│   │   └── align.py        # `bibliavox align` commands
│   ├── reference/          # Bible book catalog & versification
│   │   ├── __init__.py
│   │   ├── books.py        # 73-book Catholic Bible catalog (Book dataclass)
│   │   ├── schema.py       # Chapter/verse counts per book (BookSchema dataclass)
│   │   └── generate.py     # CLI for generating reference JSON from tdverse.csv
│   ├── text/               # Bible text acquisition & processing
│   │   ├── __init__.py
│   │   ├── source.py       # SZIT JSON loader (H_Kaldi_SZIT.json)
│   │   ├── mapping.py      # English book name → USX code (73 books)
│   │   ├── normalizer.py   # NFC unicode, whitespace, line endings
│   │   ├── jsonl_converter.py  # Nested SZIT dict → flat JSONL
│   │   ├── validator.py    # Verse count vs schema validation
│   │   ├── splitter.py     # Embedded verse marker detection & splitting
│   │   ├── mek_source.py   # mek.oszk.hu HTML scraper/parser
│   │   └── cross_validator.py  # SZIT vs MEK corpus comparison
│   ├── audio/              # Audio acquisition & processing
│   │   ├── __init__.py
│   │   ├── discovery.py    # M3U playlist parsing, manifest building
│   │   ├── downloader.py   # HTTP download with retry & batch support
│   │   ├── convert.py      # MP3 → 16kHz mono PCM WAV (ffmpeg)
│   │   ├── metadata.py     # ffprobe audio metadata extraction
│   │   ├── pipeline.py     # Orchestrates convert → metadata → seek-index
│   │   └── seek_index.py   # Sample-accurate WAV index sidecar
│   └── align/              # Transcription-based alignment
│       ├── __init__.py
│       ├── transcribe.py   # faster-whisper & VibeVoice transcription
│       └── match.py        # RapidFuzz verse-to-transcript matching
├── tests/                  # Test suite (pytest)
│   ├── __init__.py
│   ├── conftest.py         # Shared fixtures (project_root)
│   ├── test_cli_reference.py   # Reference CLI integration tests
│   ├── test_cli_text.py        # Text CLI integration tests
│   ├── test_cli_data.py        # Data CLI integration tests
│   ├── test_audio_cli.py       # Audio CLI integration tests
│   ├── test_audio_convert.py   # Audio conversion unit tests
│   ├── test_audio_discovery.py # Playlist discovery tests
│   ├── test_audio_downloader.py # Download logic tests
│   ├── test_audio_metadata.py  # Metadata extraction tests
│   ├── test_audio_pipeline.py  # Pipeline orchestration tests
│   ├── test_audio_seek_index.py # Seek index tests
│   ├── test_align.py           # Alignment pipeline tests
│   ├── test_config.py          # Configuration tests
│   ├── test_coverage.py        # Coverage audit tests
│   ├── test_cross_validator.py # Cross-validation tests
│   ├── test_generate.py        # Reference generation tests
│   ├── test_jsonl_converter.py # JSONL conversion tests
│   ├── test_mek_source.py      # MEK scraper tests
│   ├── test_reference.py       # Book catalog tests
│   ├── test_schema_fixes.py    # Schema edge case tests
│   ├── test_splitter.py        # Verse splitter tests
│   ├── test_text_mapping.py    # Book mapping tests
│   ├── test_text_normalizer.py # Normalizer tests
│   ├── test_text_source.py     # SZIT source tests
│   └── test_text_validator.py  # Validator tests
├── data/                   # Pipeline artifacts (mostly gitignored)
│   ├── reference/          # Static reference data (COMMITTED)
│   │   ├── books.json          # 73-book catalog with USX codes
│   │   ├── versification.json  # Chapter/verse counts per book
│   │   └── known_gaps.json     # Known source gaps policy
│   ├── raw/                # Original downloaded artifacts (GITIGNORED)
│   │   ├── text/               # H_Kaldi_SZIT.json
│   │   └── audio/              # Per-book MP3 dirs: {USX}/{chapter:03d}.mp3
│   ├── prepared/           # Processed audio artifacts (GITIGNORED)
│   │   └── audio/              # Per-book dirs: {USX}/{chapter:03d}.wav + .meta.json + .index.json
│   └── processed/          # Pipeline output artifacts (GITIGNORED)
│       ├── text/               # szit.jsonl, szit-fixed.jsonl, mek.jsonl, text-discrepancies.jsonl
│       ├── align/              # Transcript & match JSON per chapter per model
│       └── evaluation/         # Gold evaluation: {book}_{chapter}_{model}_matched.json, summary.json
├── docker/                 # Dockerfiles for GPU stages
│   └── Dockerfile.align    # PyTorch + CUDA + faster-whisper + transformers
├── .planning/              # GSD planning documents
│   ├── codebase/           # Codebase analysis docs (this output)
│   ├── phases/             # Phase planning documents
│   ├── research/           # Research notes
│   ├── config.json         # GSD configuration
│   ├── PROJECT.md          # Project overview
│   ├── REQUIREMENTS.md     # Requirements
│   ├── ROADMAP.md          # Roadmap
│   └── STATE.md            # Current state
├── .opencode/              # OpenCode configuration (gitignored)
├── pyproject.toml          # Python project config (hatchling build)
├── Taskfile.yml            # Task definitions (go-task)
├── docker-compose.yml      # Docker orchestration (GPU passthrough)
├── uv.lock                 # uv lockfile
├── .python-version         # Python 3.13+
├── AGENTS.md               # Agent instructions
├── README.md               # Project readme
└── SECURITY.md             # Security policy
```

## Directory Purposes

**`bibliavox/`:**
- Purpose: Main Python package — all application source code
- Contains: CLI entry, configuration, 5 sub-packages (cli, reference, text, audio, align)
- Key files: `main.py` (entry), `config.py` (settings), `coverage.py` (audit engine)

**`bibliavox/cli/`:**
- Purpose: Typer CLI subcommand group definitions
- Contains: One file per sub-command group (reference, text, audio, data, align)
- Key files: Each CLI file registers a `typer.Typer()` app that `main.py` mounts

**`bibliavox/reference/`:**
- Purpose: Bible book catalog and versification schema (static data management)
- Contains: Book dataclass, BookSchema dataclass, reference JSON generation
- Key files: `books.py` (73-book catalog), `schema.py` (verse counts), `generate.py` (JSON generation CLI)

**`bibliavox/text/`:**
- Purpose: Bible text acquisition, normalization, validation, and cross-source comparison
- Contains: SZIT JSON loading, text normalization, JSONL conversion, verse marker splitting, MEK scraping, validation
- Key files: `source.py` (SZIT loader), `jsonl_converter.py` (JSONL output), `mek_source.py` (alternate source)

**`bibliavox/audio/`:**
- Purpose: Audio discovery, download, format conversion, and metadata management
- Contains: M3U parsing, HTTP download with retry, ffmpeg conversion, ffprobe metadata, seek indexing
- Key files: `downloader.py` (batch download), `pipeline.py` (orchestration), `seek_index.py` (sample-accurate indexing)

**`bibliavox/align/`:**
- Purpose: Transcription-based verse-to-audio alignment
- Contains: Model transcription (faster-whisper, VibeVoice), RapidFuzz verse matching
- Key files: `transcribe.py` (GPU transcription), `match.py` (fuzzy matching)

**`tests/`:**
- Purpose: pytest test suite
- Contains: Unit tests and CLI integration tests for all modules
- Key files: `conftest.py` (shared fixtures), one test file per module

**`data/reference/`:**
- Purpose: Static reference data committed to git
- Contains: books.json, versification.json, known_gaps.json
- Generated: Yes (by `reference generate` command), but committed to version control

**`data/raw/`, `data/prepared/`, `data/processed/`:**
- Purpose: Pipeline artifacts at various stages
- Contains: Downloaded MP3s, prepared WAVs, processed JSONL, evaluation results
- Generated: Yes, by pipeline commands
- Committed: No (gitignored)

**`docker/`:**
- Purpose: Dockerfiles for GPU-accelerated pipeline stages
- Contains: `Dockerfile.align` (PyTorch + CUDA + faster-whisper + transformers)
- Used by: `docker-compose.yml` → `task align:evaluate-gold`

**`.planning/`:**
- Purpose: GSD workflow planning and analysis documents
- Contains: Phase plans, codebase analysis, requirements, roadmap, state tracking
- Key files: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `config.json`

## Key File Locations

**Entry Points:**
- `bibliavox/main.py`: CLI entry point — `main()` function registered as `bibliavox` console_script
- `Taskfile.yml`: Task runner entry — 20+ task definitions for all pipeline stages
- `docker-compose.yml`: Docker entry — GPU alignment service definition

**Configuration:**
- `bibliavox/config.py`: Pydantic Settings with `BIBLIAVOX_` env prefix, singleton pattern
- `pyproject.toml`: Python project metadata, dependencies, build system (hatchling)
- `.python-version`: Python 3.13+ requirement
- `Taskfile.yml`: Task definitions with vars, deps, and status checks

**Core Logic:**
- `bibliavox/reference/books.py`: 73-book Catholic Bible catalog (Book dataclass, lookup functions)
- `bibliavox/reference/schema.py`: Versification schema (BookSchema, chapter/verse counts)
- `bibliavox/text/source.py`: SZIT JSON loader with Python literal format handling
- `bibliavox/text/jsonl_converter.py`: Nested dict → flat JSONL conversion
- `bibliavox/audio/downloader.py`: Resilient HTTP download with tenacity retry
- `bibliavox/audio/pipeline.py`: Chapter preparation orchestration (convert → metadata → seek-index)
- `bibliavox/align/transcribe.py`: GPU transcription with model type dispatch
- `bibliavox/align/match.py`: RapidFuzz partial_ratio_alignment matching
- `bibliavox/coverage.py`: Dataset coverage audit with gap classification

**Testing:**
- `tests/conftest.py`: Shared fixtures (currently only `project_root`)
- `tests/test_cli_reference.py`: CLI integration tests using `typer.testing.CliRunner`

## Naming Conventions

**Files:**
- Snake_case Python modules: `jsonl_converter.py`, `seek_index.py`, `cross_validator.py`
- Test files prefixed with `test_`: `test_audio_pipeline.py`, `test_cli_text.py`
- CLI files named after sub-command group: `reference.py`, `text.py`, `audio.py`, `data.py`, `align.py`

**Directories:**
- Lowercase, single-word: `cli/`, `reference/`, `text/`, `audio/`, `align/`, `tests/`
- Data directories follow pipeline stage: `raw/`, `prepared/`, `processed/`, `reference/`

**Data Artifacts:**
- Audio files: `{USX}/{chapter:03d}.mp3` (raw), `{USX}/{chapter:03d}.wav` (prepared)
- Sidecars: `{chapter:03d}.meta.json`, `{chapter:03d}.index.json`
- Text files: `szit.jsonl`, `szit-fixed.jsonl`, `mek.jsonl`, `text-discrepancies.jsonl`
- Evaluation: `{book}_{chapter:03d}_{model_safe_name}_matched.json`, `summary.json`

## Where to Add New Code

**New CLI Command:**
- Add command function to existing `bibliavox/cli/<group>.py`
- If new sub-command group needed: create `bibliavox/cli/<name>.py`, register in `bibliavox/main.py` with `app.add_typer()`
- Add Taskfile target in `Taskfile.yml`

**New Pipeline Stage:**
- Create `bibliavox/<stage>/` package with `__init__.py`
- Create `bibliavox/cli/<stage>.py` for CLI commands
- Register in `bibliavox/main.py`
- Add data directories under `data/raw/`, `data/prepared/`, or `data/processed/`

**New Domain Model:**
- Add frozen dataclass to relevant `bibliavox/<domain>/<module>.py`
- For reference data: add to `bibliavox/reference/books.py` or `bibliavox/reference/schema.py`
- For pipeline artifacts: add TypedDict to relevant module

**New Test:**
- Create `tests/test_<module>.py` following existing naming pattern
- Use `typer.testing.CliRunner` for CLI integration tests
- Use `pytest.fixture` for test data setup
- Place unit tests alongside the module's test file

**New Configuration:**
- Add field to `BibliavoxSettings` in `bibliavox/config.py`
- Use `BIBLIAVOX_` prefix for env var name
- Add default value for optional settings

## Special Directories

**`data/reference/`:**
- Purpose: Static reference data (books.json, versification.json, known_gaps.json)
- Generated: Yes (by `bibliavox reference generate`)
- Committed: Yes — these are small, static, and version-controlled

**`data/raw/`, `data/prepared/`, `data/processed/`:**
- Purpose: Pipeline artifacts at various stages
- Generated: Yes (by pipeline commands)
- Committed: No — gitignored due to large file sizes (MP3s, WAVs)

**`.planning/`:**
- Purpose: GSD workflow planning documents
- Generated: Partially (codebase analysis docs are generated, phase plans are authored)
- Committed: Yes — project planning artifacts

**`.opencode/`:**
- Purpose: OpenCode AI tool configuration
- Generated: Yes
- Committed: No (gitignored)

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by `uv sync`)
- Committed: No (gitignored)

---

*Structure analysis: 2026-06-02*
