# External Integrations

**Analysis Date:** 2026-06-02

## APIs & External Services

**Text Source (Primary) — peterpolgar/Biblia-json-xml:**
- GitHub repository containing Hungarian Catholic Bible in JSON/XML format
- File: `H_Kaldi_SZIT.json` (Szent István Társulat translation, Unlicense license)
- Download: `curl -L` via Taskfile `text:fetch` task (`Taskfile.yml:59-64`)
- Storage: `data/raw/text/H_Kaldi_SZIT.json`
- Parser: `bibliavox/text/source.py` — loads Python literal format (single quotes) via `ast.literal_eval()`
- Module-level cache: `_SZIT_DATA` singleton (`bibliavox/text/source.py:17`)

**Text Source (Secondary/Validation) — mek.oszk.hu:**
- Hungarian Electronic Library (Magyar Elektronikus Könyvtár) HTML Bible text
- URL pattern: `https://mek.oszk.hu/00100/00176/html/{prefix}.htm`
- Encoding: ISO-8859-2 (Latin-2) decoded to UTF-8
- Parser: `bibliavox/text/mek_source.py` — BeautifulSoup4 HTML parsing
- Chapter caching: `data/raw/text/mek/{USX}_{chapter}.html`
- Output: `data/processed/text/mek.jsonl` (flat verse corpus)
- Retry: 3 attempts with exponential backoff (1-8s) via tenacity (`bibliavox/text/mek_source.py:114-118`)
- Timeout: 10.0s strict to mitigate DoS (`bibliavox/text/mek_source.py:128`)

**Audio Source — mek.oszk.hu:**
- MP3 chapter audio files hosted on MEK
- Base URL: `https://mek.oszk.hu/08800/08820/mp3` (`bibliavox/audio/discovery.py:12`)
- Playlist: `biblia.m3u` (M3U format with EXTINF metadata)
- Discovery: `bibliavox/audio/discovery.py` — parses M3U, maps to book/chapter via regex
- Download: `bibliavox/audio/downloader.py` — httpx streaming with resume support
- Storage: `data/raw/audio/{USX}/{chapter:03d}.mp3`

**Text Source (Dropped) — szentiras.eu API:**
- Previously planned primary source, now dropped
- API key config still exists: `BIBLIAVOX_SZENTIRAS_API_KEY` in `bibliavox/config.py:74`
- Empty string default (no runtime dependency)

## Data Storage

**Local Filesystem:**
- `data/raw/text/` — Downloaded source text (SZIT JSON, MEK HTML cache)
- `data/raw/audio/` — Downloaded MP3 files by book/chapter
- `data/processed/text/` — Normalized JSONL corpora (szit.jsonl, szit-fixed.jsonl, mek.jsonl)
- `data/prepared/audio/` — Converted WAV files + metadata + seek indices
- `data/reference/` — Static reference data (books.json, versification.json)
- `data/aligned/` — Alignment results (future phases)
- `data/.cache/` — Intermediate artifacts

**Databases:** None — all data is file-based (JSON, JSONL, HTML, MP3, WAV)

**Caching:**
- Module-level Python caches: `_SZIT_DATA` in `bibliavox/text/source.py`, `_BOOKS` in `bibliavox/reference/books.py`
- HTTP response caching: Chapter-level HTML files in `data/raw/text/mek/`
- Download resume: `.part` files for interrupted MP3 downloads (`bibliavox/audio/downloader.py:78`)

## Audio Processing Tools

**ffmpeg:**
- Purpose: MP3 to WAV conversion (16kHz mono PCM)
- Invocation: `subprocess.run()` in `bibliavox/audio/convert.py:58-64`
- Required output: `pcm_s16le` codec, 16000 Hz sample rate, 1 channel
- Timeout: 300 seconds per conversion
- Validation: Post-conversion probe to verify invariants (`bibliavox/audio/convert.py:76-93`)

**ffprobe:**
- Purpose: Audio metadata extraction (duration, bitrate, sample rate, channels, codec)
- Invocation: `subprocess.run()` in `bibliavox/audio/metadata.py:38-44`
- Output format: JSON (`-print_format json`)
- Timeout: 60 seconds per probe

## ML/AI Models

**faster-whisper:**
- Purpose: Speech-to-text transcription with word-level timestamps
- Usage: `bibliavox/align/transcribe.py:27-59`
- Loading: `WhisperModel(model_path, device="cuda", compute_type="float16")`
- Config: beam_size=5, language="hu", word_timestamps=True, vad_filter=True
- Default model: `large-v2` (fallback from `bofenghuang/whisper-large-v2-cv11-hu`)
- Output: List of `{word, start, end, probability}` dicts

**HuggingFace Transformers (VibeVoice pipeline):**
- Purpose: Alternative ASR via transformers pipeline
- Usage: `bibliavox/align/transcribe.py:61-94`
- Loading: `pipeline("automatic-speech-recognition", model=model_path, device="cuda:0")`
- Default model: `SZTAKI-HLT/hubert-base-cc-hu`
- Output: Chunks with text and timestamp tuples

**RapidFuzz:**
- Purpose: Fuzzy string matching between canonical verse text and transcribed words
- Usage: `bibliavox/align/match.py:4-77`
- Algorithm: `fuzz.partial_ratio_alignment()` for partial string matching
- Input: Verse texts + word transcripts with timestamps
- Output: `{verse_id, start_sec, end_sec, confidence_score}` per verse

**HuggingFace Hub:**
- Purpose: Model weight downloading for offline inference
- Usage: `bibliavox/cli/align.py:351-367` via `snapshot_download()`
- Storage: `data/models/{repo_id}/`

**Model Gauntlet Configuration:**
- Configured in `bibliavox/config.py:32-38`
- Models: `SZTAKI-HLT/hubert-base-cc-hu` (vibevoice), `bofenghuang/whisper-large-v2-cv11-hu` (faster-whisper)
- Extensible via `BIBLIAVOX_GAUNTLET` environment variable

## Authentication & Identity

**szentiras.eu API Key:**
- Config: `BIBLIAVOX_SZENTIRAS_API_KEY` (empty by default)
- Status: Dropped as text source, config retained for potential future use

**No other authentication required:**
- MEK downloads are public (no auth)
- HuggingFace Hub downloads are public models (no token required)

## Monitoring & Observability

**Error Tracking:** None — application uses stdout/stderr with rich formatting

**Logs:**
- Python `logging` module in alignment modules (`bibliavox/align/transcribe.py`, `bibliavox/align/match.py`)
- Rich `Console` output in CLI modules for user-facing messages
- No structured logging or external log aggregation

## CI/CD & Deployment

**Hosting:** Not applicable — CLI tool runs locally or in Docker

**CI Pipeline:** None detected (no `.github/workflows/`, no CI config files)

**Task Runner:**
- `task quality` — Runs all checks: lint + format-check + typecheck + test
- `task test` — Runs pytest with `-x -v` flags
- `task test-cov` — Runs pytest with coverage reporting

## Environment Configuration

**Required env vars:**
- `BIBLIAVOX_DATA_DIR` — Root data directory (default: `data/`)
- `BIBLIAVOX_CACHE_DIR` — Cache directory (default: `data/.cache/`)
- `BIBLIAVOX_REFERENCE_DATA_PATH` — Reference data path (default: `data/reference/`)
- `BIBLIAVOX_MODELS_DIR` — Model weights directory (default: `data/models/`)
- `BIBLIAVOX_SZENTIRAS_API_KEY` — szentiras.eu API key (empty default, unused)

**Secrets location:**
- `.env` file (gitignored) — Loaded by pydantic-settings
- No other secrets management detected

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None

---

*Integration audit: 2026-06-02*
