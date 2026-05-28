# Architecture Patterns

**Domain:** Bible verse-to-audio alignment CLI tool
**Researched:** 2026-05-28

## Recommended Architecture

### High-Level Data Pipeline

The tool is a **linear data pipeline with stage-based caching**. Each stage produces intermediate artifacts on disk, enabling incremental re-runs and debugging.

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌──────────┐
│  Text Fetch  │───▶│ Text Parse  │───▶│   Align      │───▶│   Export   │───▶│  Backup  │
│  (API/HTML)  │    │ (normalize) │    │ (CTC+VAD)    │    │  (JSONL)   │    │  (rsync) │
└─────────────┘    └─────────────┘    └──────────────┘    └────────────┘    └──────────┘
       │                  │                   │                   │
       ▼                  ▼                   ▼                   ▼
  data/raw/text/    data/parsed/        data/aligned/       data/export/
  (JSON per src)    (verses.json)       (per-chapter JSON)   (mappings.jsonl)
                                            ▲
┌─────────────┐    ┌─────────────┐          │
│ Audio Fetch  │───▶│ Audio Prep  │──────────┘
│ (MP3 dl)     │    │ (resample)  │
└─────────────┘    └─────────────┘
       │                  │
       ▼                  ▼
  data/raw/audio/   data/prepared/audio/
  (MP3 per ch)      (WAV 16kHz per ch)
```

### Component Boundaries

| Component | Responsibility | Communicates With | Data It Owns |
|-----------|---------------|-------------------|--------------|
| **CLI Layer** (`cli/`) | User-facing commands, argument parsing, progress display | All modules (orchestrates) | None — delegates |
| **Config** (`config.py`) | Paths, model selection, API keys, settings | All modules (injected) | `.env`, `pyproject.toml` |
| **Text Module** (`text/`) | Fetch Bible text from API/HTML, parse, normalize, cross-validate | CLI (called by), Alignment (consumed by) | `data/raw/text/`, `data/parsed/` |
| **Audio Module** (`audio/`) | Download MP3s, convert to WAV 16kHz, metadata extraction | CLI (called by), Alignment (consumed by) | `data/raw/audio/`, `data/prepared/audio/` |
| **Reference Data** (`reference/`) | Book abbreviations, USX codes, verse schema, canon order | Text, Alignment (lookups) | `data/reference/` |
| **Alignment Module** (`align/`) | Load model, generate emissions, align text to audio, produce timestamps | Text (verse data), Audio (waveforms), Export (alignment results) | `data/aligned/` |
| **Export Module** (`export/`) | Transform alignments into final JSONL with metadata | Alignment (raw results), Reference (book codes) | `data/export/` |
| **Cache Layer** (`cache/`) | Checksum-based invalidation, intermediate artifact management | All modules (wraps I/O) | `data/.cache/` |

### Module Organization (src-layout)

```
src/cath_bible_voice/
├── __init__.py
├── main.py              # Typer app entry point
├── config.py            # Pydantic Settings, paths, model config
│
├── cli/                 # One file per command group
│   ├── __init__.py
│   ├── text.py          # download-text, parse-text, validate-text
│   ├── audio.py         # download-audio, prepare-audio
│   ├── align.py         # align, align-chapter, align-all
│   ├── export.py        # export-jsonl, export-stats
│   └── backup.py        # backup, restore
│
├── text/                # Text acquisition and parsing
│   ├── __init__.py
│   ├── api_client.py    # szentiras.eu API client
│   ├── html_parser.py   # mek.oszk.hu HTML scraper
│   ├── normalizer.py    # Text normalization (Hungarian-specific)
│   └── validator.py     # Cross-source validation
│
├── audio/               # Audio acquisition and preparation
│   ├── __init__.py
│   ├── downloader.py    # MP3 download from mek.oszk.hu
│   └── preparer.py      # MP3→WAV conversion, resampling to 16kHz
│
├── reference/           # Static reference data
│   ├── __init__.py
│   ├── books.py         # Book abbreviations, USX codes, canon order
│   └── schema.py        # Verse schema (tdverse structure)
│
├── align/               # Core alignment engine
│   ├── __init__.py
│   ├── model.py         # Model loading (wav2vec2/MMS), device management
│   ├── emissions.py     # CTC emission generation
│   ├── alignment.py     # Forced alignment (Viterbi), span extraction
│   ├── text_prep.py     # Text tokenization for alignment (Hungarian)
│   └── postprocess.py   # Confidence scoring, segment merging
│
├── export/              # Output generation
│   ├── __init__.py
│   └── jsonl.py         # JSONL writer with metadata enrichment
│
└── cache/               # Caching infrastructure
    ├── __init__.py
    └── store.py         # Disk-based cache with checksum invalidation
```

## Data Flow

### Stage 1: Text Acquisition
```
szentiras.eu API ──(JSON)──▶ data/raw/text/api/{book}_{chapter}.json
mek.oszk.hu HTML ──(HTML)──▶ data/raw/text/html/{book}_{chapter}.html
```
- Each source writes raw responses to its own subdirectory
- Raw data is never modified — it's the "source of truth" for re-parsing

### Stage 2: Text Parsing & Normalization
```
data/raw/text/api/*.json ──┐
                           ├──▶ data/parsed/verses.json
data/raw/text/html/*.html ─┘
```
- Parser produces a unified verse list: `{verse_ref, book, chapter, verse, text, source}`
- Normalizer handles Hungarian diacritics, punctuation, number words
- Validator cross-checks API vs HTML sources, flags discrepancies
- **Single output file** (`verses.json`) — the canonical text representation

### Stage 3: Audio Acquisition & Preparation
```
mek.oszk.hu ──(MP3)──▶ data/raw/audio/{book}/{chapter:03d}.mp3
                              │
                              ▼
                       data/prepared/audio/{book}/{chapter:03d}.wav  (16kHz mono)
```
- MP3s downloaded per-chapter matching source structure
- Conversion to WAV 16kHz mono (required by wav2vec2 models)
- Metadata sidecar: `data/prepared/audio/{book}/{chapter:03d}.meta.json` (duration, sample_rate, channels)

### Stage 4: Alignment
```
data/parsed/verses.json ──────────────┐
                                      ▼
data/prepared/audio/{book}/{ch}.wav ──▶ align engine ──▶ data/aligned/{book}/{chapter:03d}.json
```
- Per-chapter alignment: takes verses for one chapter + corresponding WAV
- Alignment output per chapter:
  ```json
  {
    "book": "GEN", "chapter": 1,
    "audio_file": "data/prepared/audio/GEN/001.wav",
    "duration_sec": 245.3,
    "model": "sarpba/wav2vec2-large-xlsr-53-hungarian",
    "verses": [
      {
        "verse_ref": "GEN_1_1",
        "verse_num": 1,
        "text": "Kezdetben teremtette Isten az eget és a földet.",
        "start_sec": 0.0,
        "end_sec": 4.52,
        "confidence": 0.94,
        "words": [
          {"word": "Kezdetben", "start_sec": 0.0, "end_sec": 0.82, "score": 0.97},
          ...
        ]
      }
    ]
  }
  ```
- **Intermediate emissions cached** as `.npy` files in `data/.cache/emissions/` — expensive to recompute, cheap to reload

### Stage 5: Export
```
data/aligned/**/*.json ──▶ data/export/mappings.jsonl
```
- Flattens per-chapter alignments into single JSONL
- Enriches with metadata: translation, narrator, source URLs, processing timestamps
- Each line:
  ```json
  {"verse_ref": "GEN_1_1", "audio_file": "GEN/001.mp3", "start_sec": 0.0, "end_sec": 4.52, "source": "mek.oszk.hu", "translation": "SZIT", "narrator": "unknown", "confidence": 0.94, "model": "sarpba/wav2vec2-large-xlsr-53-hungarian", "aligned_at": "2026-05-28T12:00:00Z"}
  ```

### Stage 6: Backup
```
data/ ──(rsync)──▶ remote SFTP host
```

## Patterns to Follow

### Pattern 1: Stage-Based Caching with Checksums
**What:** Each pipeline stage checks if its output already exists and if inputs haven't changed before re-running.
**When:** Every stage that has expensive computation (alignment, audio conversion).
**Example:**
```python
from cath_bible_voice.cache.store import CacheStore

cache = CacheStore("data/.cache")

def align_chapter(book: str, chapter: int) -> dict:
    input_key = f"{book}/{chapter:03d}"
    input_hash = cache.hash_inputs(
        f"data/parsed/verses.json#{book}:{chapter}",
        f"data/prepared/audio/{book}/{chapter:03d}.wav",
    )
    
    cached = cache.get("alignment", input_key, input_hash)
    if cached is not None:
        return cached
    
    # ... run alignment ...
    result = run_alignment(verses, audio_path)
    cache.put("alignment", input_key, input_hash, result)
    return result
```

### Pattern 2: Protocol-Based Module Interfaces
**What:** Define interfaces (Protocols) for each module so implementations can be swapped (e.g., different alignment models, different text sources).
**When:** When a module has multiple implementations (API vs HTML text source, wav2vec2 vs MMS model).
**Example:**
```python
from typing import Protocol

class TextSource(Protocol):
    def fetch_chapter(self, book: str, chapter: int) -> list[Verse]: ...
    def fetch_book_list(self) -> list[BookInfo]: ...

class ApiTextSource:
    """Implements TextSource via szentiras.eu API"""
    ...

class HtmlTextSource:
    """Implements TextSource via mek.oszk.hu HTML scraping"""
    ...
```

### Pattern 3: Per-Chapter Processing Unit
**What:** The chapter is the fundamental processing unit. All stages operate on one chapter at a time.
**When:** Throughout the pipeline — download, parse, align, export all work chapter-by-chapter.
**Why:** Matches the audio source structure (per-chapter MP3s), enables parallelism, limits memory usage, allows incremental processing.

### Pattern 4: Typer Sub-Command Groups
**What:** Each module gets its own Typer sub-app, registered via `add_typer`.
**When:** CLI layer organization.
**Example:**
```python
# main.py
import typer
from cath_bible_voice.cli import text, audio, align, export, backup

app = typer.Typer(name="cbv", help="Catholic Bible Voice alignment tool")
app.add_typer(text.app, name="text", help="Bible text operations")
app.add_typer(audio.app, name="audio", help="Audio operations")
app.add_typer(align.app, name="align", help="Alignment operations")
app.add_typer(export.app, name="export", help="Export operations")
app.add_typer(backup.app, name="backup", help="Backup operations")
```

### Pattern 5: Rich Progress for Long Operations
**What:** Use `rich.progress` for alignment and download operations that take significant time.
**When:** Any operation processing multiple chapters or large audio files.
**Example:**
```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Aligning Genesis...", total=50)  # 50 chapters
    for chapter in chapters:
        align_chapter(book, chapter)
        progress.advance(task)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Alignment Function
**What:** A single function that loads model, fetches text, loads audio, aligns, and exports all at once.
**Why bad:** Impossible to debug individual stages, can't cache intermediate results, can't swap components.
**Instead:** Separate model loading, emission generation, alignment, and post-processing into distinct functions that can be composed. The `ctc-forced-aligner` library demonstrates this well: `load_audio → load_model → generate_emissions → preprocess_text → get_alignments → get_spans → postprocess_results`.

### Anti-Pattern 2: In-Memory-Only Pipeline
**What:** Keeping all intermediate data in memory without writing to disk.
**Why bad:** 73 books × ~30 chapters = ~2000 chapters of audio. If alignment fails at chapter 1500, everything is lost. Memory usage grows unbounded.
**Instead:** Write intermediate artifacts to disk at each stage boundary. Use `data/aligned/{book}/{chapter}.json` as checkpoints.

### Anti-Pattern 3: Hardcoded Model Paths
**What:** Embedding model names/paths directly in alignment code.
**Why bad:** Can't experiment with different models (Hungarian-specific vs MMS multilingual), can't upgrade models without code changes.
**Instead:** Model selection via config (`config.py` with Pydantic Settings), supporting `--model` CLI flag.

### Anti-Pattern 4: Mixing Download and Processing
**What:** Downloading audio/text and immediately processing in the same function.
**Why bad:** Network failures corrupt processing state. Can't re-process without re-downloading. Violates the principle of separating I/O from computation.
**Instead:** Download tasks write raw files. Processing tasks read from raw files. They are independent Taskfile targets.

### Anti-Pattern 5: Ignoring Hungarian Text Normalization
**What:** Passing raw Bible text directly to the alignment model without normalization.
**Why bad:** CTC models have limited vocabularies. Hungarian diacritics (á, é, í, ó, ö, ő, ú, ü, ű), punctuation, and verse numbers need normalization. The MMS forced aligner uses a restricted Latin vocabulary — text must be lowercased and stripped of non-alphabetic characters for tokenization.
**Instead:** Dedicated `text_prep.py` in the align module that normalizes text specifically for the chosen model's tokenizer.

## Alignment Model Architecture Decision

### Recommended: Two-Strategy Approach

**Strategy A — Hungarian-specific wav2vec2 (primary):**
- Model: `sarpba/wav2vec2-large-xlsr-53-hungarian` (WER 17.3% on Common Voice 17.0)
- Native Hungarian vocabulary — no romanization needed
- Better accuracy for Hungarian speech
- Use with `ctc-forced-aligner` library

**Strategy B — MMS multilingual (fallback/comparison):**
- Model: `MahmoudAshraf/mms-300m-1130-forced-aligner` (supports 1130+ languages)
- Requires text romanization (Hungarian already uses Latin script, minimal normalization)
- Broader language support for future translations
- Purpose-built for forced alignment (not ASR)

**Why both:** The Hungarian-specific model should be more accurate for this specific use case, but the MMS model is purpose-built for alignment and may handle edge cases better. Having both allows comparison and confidence scoring.

### Model Loading Pattern
```python
# align/model.py
def load_alignment_model(
    model_name: str = "sarpba/wav2vec2-large-xlsr-53-hungarian",
    device: str = "cuda",
    dtype: torch.dtype = torch.float16,
) -> tuple[Wav2Vec2ForCTC, Wav2Vec2Processor]:
    """Load model once, reuse for all chapters in a batch."""
    model = Wav2Vec2ForCTC.from_pretrained(model_name).to(device).to(dtype)
    processor = Wav2Vec2Processor.from_pretrained(model_name)
    return model, processor
```

**Key insight from easyaligner:** Load the model once per batch run, not per chapter. Model loading takes seconds; alignment per chapter takes milliseconds to seconds. The CLI should load the model at the start of `align-all` and pass it through.

## Scalability Considerations

| Concern | At 73 books (v1) | At 200+ books (multi-translation) | At 1000+ audio sources |
|---------|-------------------|-----------------------------------|----------------------|
| **Storage** | ~2GB audio + ~50MB text + ~100MB aligned | ~10GB | ~50GB+ |
| **Processing time** | ~2-4 hours (GPU) | ~10-20 hours | Days |
| **Memory** | Single chapter in memory (~30MB WAV) | Same | Same |
| **Parallelism** | Sequential per chapter is fine | Consider per-book parallelism | Need worker pool |
| **Cache size** | ~500MB emissions cache | ~2GB | ~10GB, need eviction |

**v1 approach:** Sequential chapter-by-chapter processing with a single GPU model instance. No need for distributed processing. The 3090 handles one chapter at a time efficiently.

**Future:** If processing many translations/narrators, the per-chapter design naturally enables `multiprocessing` or `concurrent.futures` with one model per GPU (or shared model with thread-safe inference).

## Suggested Build Order (Dependencies)

```
Phase 1: Foundation
  ├── config.py (paths, settings)
  ├── reference/ (book data, USX codes)
  └── cache/store.py (disk cache)

Phase 2: Text Pipeline (independently testable)
  ├── text/api_client.py
  ├── text/html_parser.py
  ├── text/normalizer.py
  └── text/validator.py

Phase 3: Audio Pipeline (independently testable)
  ├── audio/downloader.py
  └── audio/preparer.py

Phase 4: Alignment Engine (depends on Phase 2 + 3)
  ├── align/model.py
  ├── align/text_prep.py
  ├── align/emissions.py
  ├── align/alignment.py
  └── align/postprocess.py

Phase 5: Export & CLI (depends on Phase 4)
  ├── export/jsonl.py
  ├── cli/*.py (all command groups)
  └── main.py (entry point)

Phase 6: Operations
  └── backup/ (rsync tasks)
```

**Why this order:**
- Phases 2 and 3 are independent — can be built in parallel or either first
- Phase 4 is the critical path — depends on both text and audio outputs
- Phase 5 wraps everything into the user-facing interface
- Each phase produces testable artifacts before the next phase begins

## Taskfile ↔ Module Mapping

| Taskfile Target | Module | Description |
|----------------|--------|-------------|
| `download-text` | `text/api_client.py`, `text/html_parser.py` | Fetch raw text from both sources |
| `parse-text` | `text/normalizer.py` | Parse raw → `data/parsed/verses.json` |
| `validate-text` | `text/validator.py` | Cross-validate sources |
| `download-audio` | `audio/downloader.py` | Download MP3s |
| `prepare-audio` | `audio/preparer.py` | Convert MP3 → WAV 16kHz |
| `align` | `align/*` | Run alignment for one chapter |
| `align-all` | `align/*` | Run alignment for all chapters |
| `export` | `export/jsonl.py` | Generate final JSONL |
| `backup` | (Taskfile shell) | rsync to remote |

## Sources

- **easyaligner** (kb-labb): Modular 3-stage pipeline (VAD → emissions → alignment) with intermediate caching — https://github.com/kb-labb/easyaligner [HIGH confidence, official docs]
- **ctc-forced-aligner** (MahmoudAshraf97): Linear CTC alignment pipeline with MMS model support — https://github.com/MahmoudAshraf97/ctc-forced-aligner [HIGH confidence, official repo]
- **MMS 300M forced aligner**: 1130+ language support including Hungarian — https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner [HIGH confidence, HuggingFace model card]
- **sarpba/wav2vec2-large-xlsr-53-hungarian**: Best Hungarian wav2vec2 model (WER 17.3%) — https://huggingface.co/sarpba/wav2vec2-large-xlsr-53-hungarian [HIGH confidence, HuggingFace model card]
- **Typer documentation**: Sub-command patterns with `add_typer` — https://typer.tiangolo.com/tutorial/one-file-per-command/ [HIGH confidence, official docs]
- **Python packaging**: src-layout best practices — https://packaging.python.org/en/latest/guides/creating-command-line-tools/ [HIGH confidence, official docs]
