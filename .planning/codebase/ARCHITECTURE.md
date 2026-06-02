<!-- refreshed: 2026-06-02 -->
# Architecture

**Analysis Date:** 2026-06-02

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Layer (Typer)                             │
│  `bibliavox/main.py`                                                │
├────────────┬────────────┬──────────────┬────────────┬───────────────┤
│ reference  │    text    │    audio     │    data    │     align     │
│ `cli/`     │ `cli/`     │ `cli/`      │ `cli/`    │ `cli/`        │
│ reference  │ text       │ audio       │ data      │ align         │
│ .py        │ .py        │ .py         │ .py       │ .py           │
└─────┬──────┴─────┬──────┴──────┬───────┴─────┬─────┴───────┬───────┘
      │            │             │             │             │
      ▼            ▼             ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│reference/│ │  text/   │ │  audio/  │ │coverage  │ │   align/     │
│books.py  │ │source.py │ │discovery │ │  .py     │ │transcribe.py │
│schema.py │ │normalizer│ │downloader│ │          │ │match.py      │
│generate  │ │jsonl_conv│ │convert   │ │          │ │              │
│.py       │ │mapping.py│ │pipeline  │ │          │ │              │
│          │ │validator │ │metadata  │ │          │ │              │
│          │ │splitter  │ │seek_index│ │          │ │              │
│          │ │mek_source│ │          │ │          │ │              │
│          │ │cross_val │ │          │ │          │ │              │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘
      │            │             │             │             │
      ▼            ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                  │
│  `data/reference/`    `data/raw/`    `data/prepared/`  `data/processed/` │
│  books.json           text/          audio/            text/         │
│  versification.json   audio/                         evaluation/    │
│  known_gaps.json                                       align/       │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  External Sources                                                   │
│  szentiras.eu API    mek.oszk.hu MP3/HTML    HuggingFace models     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI Entry | Typer app registration, sub-command routing | `bibliavox/main.py` |
| Config | Pydantic Settings singleton, env var loading | `bibliavox/config.py` |
| Reference CLI | Book listing, lookup, info, reference generation | `bibliavox/cli/reference.py` |
| Text CLI | Fetch, normalize, validate, convert-jsonl, fix-verses, ingest-mek, cross-validate | `bibliavox/cli/text.py` |
| Audio CLI | Download, convert, info, prepare, seek, batch ops | `bibliavox/cli/audio.py` |
| Data CLI | Coverage audit with gap classification | `bibliavox/cli/data.py` |
| Align CLI | Transcribe, match, evaluate-gold, setup (model download) | `bibliavox/cli/align.py` |
| Books Catalog | 73-book Catholic Bible catalog with USX codes | `bibliavox/reference/books.py` |
| Versification | Chapter/verse counts per book from szentiras.eu | `bibliavox/reference/schema.py` |
| Reference Gen | Generate books.json + versification.json from tdverse.csv | `bibliavox/reference/generate.py` |
| SZIT Source | Load H_Kaldi_SZIT.json (Python literal format) | `bibliavox/text/source.py` |
| Book Mapping | English book name → USX code (73 books) | `bibliavox/text/mapping.py` |
| Normalizer | NFC unicode, whitespace collapse, line ending fix | `bibliavox/text/normalizer.py` |
| JSONL Converter | Nested SZIT dict → flat JSONL with USX codes | `bibliavox/text/jsonl_converter.py` |
| Validator | Verse count vs schema validation, severity-based reporting | `bibliavox/text/validator.py` |
| Splitter | Embedded verse marker detection and splitting | `bibliavox/text/splitter.py` |
| MEK Source | HTML scraper for mek.oszk.hu alternate text corpus | `bibliavox/text/mek_source.py` |
| Cross Validator | SZIT vs MEK corpus comparison | `bibliavox/text/cross_validator.py` |
| Audio Discovery | M3U playlist parsing, manifest building, inventory | `bibliavox/audio/discovery.py` |
| Audio Downloader | Resilient HTTP download with retry, batch parallelism | `bibliavox/audio/downloader.py` |
| Audio Converter | MP3 → 16kHz mono PCM WAV via ffmpeg | `bibliavox/audio/convert.py` |
| Audio Metadata | ffprobe-based audio inspection | `bibliavox/audio/metadata.py` |
| Audio Pipeline | Orchestrates convert → metadata → seek-index | `bibliavox/audio/pipeline.py` |
| Seek Index | Sample-accurate WAV index sidecar + preview extraction | `bibliavox/audio/seek_index.py` |
| Transcriber | faster-whisper and VibeVoice model transcription | `bibliavox/align/transcribe.py` |
| Matcher | RapidFuzz partial_ratio_alignment verse matching | `bibliavox/align/match.py` |
| Coverage Audit | Text+audio dataset coverage with gap classification | `bibliavox/coverage.py` |

## Pattern Overview

**Overall:** CLI Pipeline Architecture — each pipeline stage is a Typer sub-command group backed by a dedicated package. Stages produce artifacts in the `data/` directory tree that downstream stages consume.

**Key Characteristics:**
- **Flat Python package** (`bibliavox/`) with sub-packages per pipeline domain (`reference/`, `text/`, `audio/`, `align/`)
- **CLI-first interface** — every operation is a Typer command; no web server or API layer
- **File-based data flow** — stages communicate through JSON/JSONL/WAV files in `data/`
- **Module-level caches** — books, schemas, SZIT data, and mappings use `_GLOBAL` singletons with lazy loading
- **Docker for GPU only** — heavy model inference runs in Docker with NVIDIA GPU passthrough; everything else runs native Python

## Layers

**CLI Layer:**
- Purpose: User-facing command interface, argument parsing, output formatting
- Location: `bibliavox/cli/` and `bibliavox/main.py`
- Contains: Typer sub-apps, Rich console output, input validation
- Depends on: All domain packages (`reference/`, `text/`, `audio/`, `align/`, `coverage.py`)
- Used by: User (terminal), Taskfile targets, Docker entrypoint

**Domain Layer:**
- Purpose: Business logic for each pipeline stage
- Location: `bibliavox/reference/`, `bibliavox/text/`, `bibliavox/audio/`, `bibliavox/align/`
- Contains: Data loading, transformation, validation, external API calls
- Depends on: `config.py`, other domain packages (e.g., `text/` depends on `reference/`)
- Used by: CLI layer

**Configuration Layer:**
- Purpose: Centralized settings with env var and .env file support
- Location: `bibliavox/config.py`
- Contains: `BibliavoxSettings` (Pydantic BaseSettings), `ModelConfig`, `ModelGauntletSettings`
- Depends on: pydantic-settings
- Used by: All domain packages via `get_settings()`

**Data Layer:**
- Purpose: Persistent artifact storage (not a database — filesystem-based)
- Location: `data/` directory tree
- Contains: Reference JSON, raw audio MP3s, prepared WAVs, processed JSONL, evaluation results
- Depends on: Nothing (passive storage)
- Used by: All layers read/write here

## Data Flow

### Primary Pipeline: Text Acquisition → Alignment

1. **Reference Generation** (`bibliavox/reference/generate.py`)
   - Input: szentiras.eu tdverse.csv (fetched from GitHub)
   - Output: `data/reference/books.json`, `data/reference/versification.json`
   - Trigger: `task reference:generate`

2. **Text Acquisition** (`bibliavox/text/source.py`, `bibliavox/text/mek_source.py`)
   - Input: GitHub raw SZIT JSON download, mek.oszk.hu HTML pages
   - Output: `data/raw/text/H_Kaldi_SZIT.json`
   - Trigger: `task text:fetch`, `task text:ingest-mek`

3. **Text Normalization & Conversion** (`bibliavox/text/normalizer.py`, `bibliavox/text/jsonl_converter.py`)
   - Input: `data/raw/text/H_Kaldi_SZIT.json`
   - Process: NFC normalization → JSONL with USX codes → verse marker fixing
   - Output: `data/processed/text/szit.jsonl` → `data/processed/text/szit-fixed.jsonl`, `data/processed/text/mek.jsonl`
   - Trigger: `task text:convert-jsonl`, `task text:fix-verses`

4. **Text Validation** (`bibliavox/text/validator.py`, `bibliavox/text/cross_validator.py`)
   - Input: Processed JSONL + versification schema
   - Process: Verse count validation, SZIT vs MEK cross-validation
   - Output: Validation reports, `data/processed/text/text-discrepancies.jsonl`
   - Trigger: `task text:validate`, `task text:cross-validate`

5. **Audio Download** (`bibliavox/audio/discovery.py`, `bibliavox/audio/downloader.py`)
   - Input: mek.oszk.hu M3U playlist
   - Process: Parse playlist → build manifest → parallel download with retry
   - Output: `data/raw/audio/{USX}/{chapter:03d}.mp3`
   - Trigger: `task audio:download-all`

6. **Audio Preparation** (`bibliavox/audio/pipeline.py`)
   - Input: `data/raw/audio/{USX}/{chapter:03d}.mp3`
   - Process: MP3 → 16kHz mono WAV (ffmpeg) → metadata probe → seek index build
   - Output: `data/prepared/audio/{USX}/{chapter:03d}.wav`, `.meta.json`, `.index.json`
   - Trigger: `task audio:prepare-all`

7. **Coverage Audit** (`bibliavox/coverage.py`)
   - Input: All text + audio artifacts
   - Process: Compare expected (schema) vs actual (files), classify gaps
   - Output: Coverage report with gap classification
   - Trigger: `task data:coverage`

8. **Alignment** (`bibliavox/align/transcribe.py`, `bibliavox/align/match.py`)
   - Input: Prepared WAVs + processed text JSONL
   - Process: Transcribe (faster-whisper/VibeVoice) → RapidFuzz matching → timestamp extraction
   - Output: `data/processed/evaluation/{book}_{chapter}_{model}_matched.json`, `summary.json`
   - Trigger: `task align:evaluate-gold` (Docker with GPU)

**State Management:**
- No runtime state between commands — each CLI invocation is stateless
- Module-level caches (`_BOOKS`, `_SCHEMAS`, `_SZIT_DATA`, `_MAPPING`) provide lazy-loaded singletons within a single process
- All persistent state lives in the `data/` filesystem tree
- `reset_settings()` available in `config.py` for test isolation

## Key Abstractions

**Book:**
- Purpose: Represents a single Catholic Bible book with metadata
- Examples: `bibliavox/reference/books.py:28` (`Book` dataclass)
- Pattern: Frozen dataclass with slots, loaded from `data/reference/books.json`

**BookSchema:**
- Purpose: Versification data (chapter count, verse counts per chapter)
- Examples: `bibliavox/reference/schema.py:24` (`BookSchema` dataclass)
- Pattern: Frozen dataclass, loaded from `data/reference/versification.json`

**ManifestItem:**
- Purpose: Canonical chapter audio record from M3U playlist
- Examples: `bibliavox/audio/discovery.py:22` (TypedDict)
- Pattern: TypedDict with book_usx, chapter, url, relative_path, extinf_sec, source

**ModelConfig / ModelGauntletSettings:**
- Purpose: Alignment model configuration (ID + type)
- Examples: `bibliavox/config.py:23` (Pydantic BaseModel)
- Pattern: Nested Pydantic models inside BibliavoxSettings

**Discrepancy:**
- Purpose: Validation finding with severity level
- Examples: `bibliavox/text/validator.py:33` (frozen dataclass)
- Pattern: Frozen dataclass with Severity enum (ERROR/WARNING/INFO)

## Entry Points

**CLI Entry:**
- Location: `bibliavox/main.py:29` (`main()`)
- Triggers: `uv run bibliavox ...`, console_scripts entry in pyproject.toml
- Responsibilities: Register 5 sub-command groups (reference, text, audio, data, align), delegate to Typer

**Taskfile Targets:**
- Location: `Taskfile.yml`
- Triggers: `task <target-name>`
- Responsibilities: Orchestrate multi-step workflows, manage dependencies between tasks

**Docker Entrypoint:**
- Location: `docker-compose.yml`
- Triggers: `docker compose run --rm align ...`
- Responsibilities: GPU-accelerated alignment pipeline execution

## Architectural Constraints

- **Threading:** Single-threaded by default; `audio/downloader.py` uses `ThreadPoolExecutor` for parallel downloads (configurable worker count)
- **Global state:** Module-level caches in `books.py` (`_BOOKS`), `schema.py` (`_SCHEMAS`), `source.py` (`_SZIT_DATA`), `mapping.py` (`_MAPPING`), `config.py` (`_settings`). These are process-scoped singletons. Use `reset_settings()` in tests.
- **Circular imports:** None detected. Dependency graph flows: `cli/` → `reference/`, `text/`, `audio/`, `align/`, `coverage.py`. Cross-package dependencies are minimal (`text/` imports from `reference/`, `audio/` imports from `reference/`, `coverage.py` imports from `reference/`, `text/`, `audio/`).
- **External tool dependency:** ffmpeg and ffprobe must be on PATH for audio conversion/metadata operations
- **GPU dependency:** Alignment transcription requires NVIDIA GPU with CUDA; runs in Docker container only
- **Data directory coupling:** All modules use relative paths from repo root (`data/`); no absolute path hardcoding except in `_REPO_ROOT` computations

## Anti-Patterns

### Module-Level Global Caches

**What happens:** `books.py`, `schema.py`, `source.py`, `mapping.py` each maintain module-level `_GLOBAL` variables that cache loaded data indefinitely within a process.
**Why it's wrong:** Makes testing harder (stale cache between tests), prevents concurrent configuration, creates hidden dependencies.
**Do this instead:** Use dependency injection or pass data explicitly. For tests, call `reset_settings()` and clear module globals.

### Inline Imports in CLI Commands

**What happens:** Several CLI commands (e.g., `text.py:357`, `text.py:399`, `cli/align.py:351`) import domain modules inside the function body rather than at module top.
**Why it's wrong:** Hides dependencies, makes import errors surface late at runtime instead of at startup.
**Do this instead:** Move all imports to module top-level. The inline pattern was likely used to defer heavy imports (like `huggingface_hub`), but these should be gated by the Docker environment, not by import location.

## Error Handling

**Strategy:** Exception-based with custom exception classes per domain, Rich console error output, and `typer.Exit(code=1)` for CLI failure paths.

**Patterns:**
- Custom exception classes: `AudioConversionError` (`audio/convert.py:16`), `AudioProbeError` (`audio/metadata.py:12`), `SeekIndexError` (`audio/seek_index.py:11`)
- HTTP retry with tenacity: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))` in `audio/downloader.py:37`
- Graceful degradation: Missing books/chapters produce warnings, not fatal errors (e.g., `reference/generate.py:684`)
- Rich console error output: `console.print(f"[red]Error message[/red]")` pattern throughout all CLI modules
- Exit codes: `typer.Exit(code=1)` for failures, `typer.Exit(code=0)` for success

## Cross-Cutting Concerns

**Logging:** Python `logging` module used in `align/transcribe.py` and `align/match.py` only. All other modules use Rich `Console.print()` for user-facing output. No structured logging framework.

**Validation:** Pydantic for configuration (`config.py`), manual validation in CLI argument handlers, `validator.py` for text schema validation.

**Authentication:** szentiras.eu API key via `BIBLIAVOX_SZENTIRAS_API_KEY` env var (currently unused — text sourced from GitHub JSON instead).

---

*Architecture analysis: 2026-06-02*
