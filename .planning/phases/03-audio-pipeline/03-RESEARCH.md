# Phase 3: Audio Pipeline - Research

**Researched:** 2026-05-29  
**Domain:** Audio acquisition, normalization, and seek-accurate preprocessing for Hungarian Bible narration  
**Confidence:** HIGH

## User Constraints

No `03-CONTEXT.md` exists yet in this phase directory, so there are no phase-specific locked decisions beyond roadmap/requirements and AGENTS constraints. [VERIFIED: codebase grep]

## Project Constraints (from AGENTS.md)

- Use Python 3.13+ and `uv` as package manager. [VERIFIED: AGENTS.md, pyproject.toml]
- Keep CLI in Typer patterns used by existing `bibliavox` command groups. [VERIFIED: AGENTS.md, bibliavox/main.py]
- Keep workflow via Taskfile (`task`/go-task targets are required deliverables). [VERIFIED: AGENTS.md, Taskfile.yml]
- Keep model-heavy stages in Docker, but this audio phase is a lightweight native Python stage. [VERIFIED: AGENTS.md]
- Each phase must deliver working Typer command(s) and Taskfile target(s). [VERIFIED: AGENTS.md]

## Summary

Phase 3 should treat MEK’s `biblia.m3u` as the source of truth for chapter MP3 discovery and expected durations. It already contains per-track durations (`#EXTINF`) and relative paths for all published chapter MP3 files, and it resolves to 1328 MP3 entries across 73 book folders. [VERIFIED: MEK m3u runtime parse] The playlist is structurally reliable, but it does not exactly match your current versification counts (notably EST, DAN, MAL), so the downloader must support “available-on-source” reality and emit discrepancy reports instead of hard-failing all-bible runs. [VERIFIED: versification vs m3u diff runtime]

For robustness, use `httpx.Client` connection pooling + explicit timeout classes + bounded retries (Tenacity) for network IO, and use `ffmpeg`/`ffprobe` subprocess calls for conversion and metadata verification. [CITED: https://www.python-httpx.org/advanced/clients/] [CITED: https://www.python-httpx.org/advanced/timeouts/] [CITED: https://tenacity.readthedocs.io/en/latest/] [CITED: https://ffmpeg.org/ffprobe.html] This aligns with existing project dependencies and avoids hand-rolled media parsing.

**Primary recommendation:** Build Phase 3 around a generated manifest from `biblia.m3u`, then implement `audio download`, `audio convert`, and `audio info` as idempotent, resumable, task-oriented commands with strict post-step validation (`ffprobe` JSON checks + duration-drift check against playlist `#EXTINF`). [VERIFIED: MEK m3u + project stack]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MP3 discovery from MEK playlist | API/Backend (CLI runtime) | CDN/Static | HTTP retrieval + parsing is backend responsibility; source is static-hosted files. [VERIFIED: MEK index + m3u] |
| Parallel/resumable downloading | API/Backend | — | Concurrency, retries, resume logic, and filesystem writes are backend concerns. [CITED: httpx docs] |
| MP3→WAV normalization | API/Backend | — | Deterministic offline transform via ffmpeg subprocess. [CITED: https://ffmpeg.org/ffmpeg.html] |
| Audio metadata extraction | API/Backend | — | ffprobe JSON extraction and reporting in CLI output. [CITED: https://ffmpeg.org/ffprobe.html] |
| Seek index generation | API/Backend | Database/Storage | Index files are persisted artifacts consumed later by alignment pipeline. [ASSUMED] |

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUD-01 | Download per-chapter MP3 files from mek.oszk.hu with retry and resume | M3U-based manifest, HTTP range validation (`Accept-Ranges: bytes`), Tenacity retry policy, resume via temp-part file + Range requests. [VERIFIED: curl HEAD + MEK m3u] |
| AUD-02 | Parallel download of multiple chapters with configurable concurrency | `httpx.Client` pooling + configurable worker count + Rich progress bars. [CITED: httpx clients/timeouts docs; Rich progress docs] |
| AUD-03 | Decode MP3 to WAV 16kHz mono | ffmpeg conversion command + ffprobe verification checks (`sample_rate=16000`, `channels=1`, `pcm_s16le`). [VERIFIED: local ffmpeg/ffprobe run] |
| AUD-04 | Extract audio metadata (bitrate, sample rate, duration) per file | ffprobe JSON as canonical extractor; optional Mutagen for MP3 tags if needed. [CITED: ffprobe docs] [CITED: mutagen docs] |
| AUD-05 | Build seek index for accurate timestamp access in WAV files | Store sample-accurate index metadata (sample_rate + total_samples + chapter offsets), avoid MP3-timebase seeking downstream. [ASSUMED] |
</phase_requirements>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| httpx | 0.28.1 (uploaded 2024-12-06) | Download MP3 + playlist with client pooling/timeouts | Already in project deps; supports per-phase network controls. [VERIFIED: pyproject.toml] [VERIFIED: PyPI JSON query] [CITED: httpx docs] |
| tenacity | 9.1.4 (uploaded 2026-02-07) | Retry/backoff policies for transient HTTP failures | Clean retry composition; avoids custom retry loops. [VERIFIED: PyPI JSON query] [CITED: tenacity docs] |
| ffmpeg (CLI) | 7.1.4 (local) | MP3→WAV (16k mono PCM) conversion | Battle-tested audio decode/resample. [VERIFIED: local tool version] [CITED: ffmpeg docs] |
| ffprobe (CLI) | 7.1.4 (local) | Machine-readable media validation/metadata | Produces parseable JSON and stream-level fields. [VERIFIED: local tool version] [CITED: ffprobe docs] |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|--------------|---------|---------|-------------|
| rich | 15.0.0 (uploaded 2026-04-12) | Multi-task progress UI for downloads/conversions | Use for `--all` and long-running chapter batches. [VERIFIED: PyPI JSON query] [CITED: Rich progress docs] |
| typer | 0.26.3 (uploaded 2026-05-28) | CLI command/options and subcommand group wiring | Use existing `add_typer(..., name="audio")` pattern. [VERIFIED: PyPI JSON query] [CITED: Typer docs] |
| mutagen (optional) | 1.47.0 (uploaded 2023-09-03) | MP3 tag/length fallback if ffprobe unavailable | Optional fallback only; ffprobe remains canonical. [VERIFIED: PyPI JSON query] [CITED: mutagen docs] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx + tenacity | `requests` + `urllib3.Retry` | Works, but diverges from current dependency set and reduces consistency with existing codebase. [ASSUMED] |
| ffprobe JSON metadata | mutagen-only metadata | Mutagen is Python-native but weaker for strict decode/stream verification than ffprobe. [CITED: mutagen docs] [CITED: ffprobe docs] |
| M3U discovery | HTML link scraping of `index.html` | HTML parsing is noisier and less stable than playlist semantics already intended for track listing. [VERIFIED: MEK index + m3u]

**Installation:**
```bash
uv add tenacity
```

No other new Python dependency is required for baseline implementation because `httpx`, `typer`, and `rich` are already declared, and ffmpeg/ffprobe are available in environment. [VERIFIED: pyproject.toml] [VERIFIED: environment audit]

## Architecture Patterns

### System Architecture Diagram

```text
                +---------------------------+
                |  MEK mp3/index + biblia.m3u |
                +-------------+-------------+
                              |
                              v
                   [audio discover/build-manifest]
                              |
                +-------------+-------------+
                | chapter manifest JSONL    |
                | (url, extinf_sec, book/ch)|
                +-------------+-------------+
                              |
                 +------------+-------------+
                 |                          |
                 v                          v
      [audio download --book/ch]   [audio download --all --workers N]
                 |                          |
                 +------------+-------------+
                              v
                  data/raw/audio/{USX}/{ch}.mp3
                              |
                              v
                [audio convert -> ffmpeg subprocess]
                              |
                              v
                data/prepared/audio/{USX}/{ch}.wav
                              |
                              v
                  [audio verify/info -> ffprobe]
                              |
                              v
      data/prepared/audio/{USX}/{ch}.meta.json + seek-index sidecar
```

### Recommended Project Structure

```text
bibliavox/
├── audio/
│   ├── discovery.py      # M3U parsing, chapter manifest build
│   ├── downloader.py     # resume/retry/parallel download orchestration
│   ├── convert.py        # ffmpeg invocation + WAV conversion
│   ├── metadata.py       # ffprobe parsing + normalization
│   └── seek_index.py     # WAV sample index sidecar
├── cli/
│   └── audio.py          # Typer commands for download/convert/info
└── main.py               # add_typer(audio.app, name="audio")

data/
├── raw/audio/{USX}/{chapter:03d}.mp3
└── prepared/audio/{USX}/{chapter:03d}.{wav,meta.json,index.json}
```

### Pattern 1: Playlist-first discovery
**What:** Generate chapter manifest from `biblia.m3u` (`#EXTINF` + relative MP3 path). [VERIFIED: MEK m3u]
**When to use:** Always, before any chapter download.
**Example:**
```python
# Source: https://mek.oszk.hu/08800/08820/mp3/biblia.m3u
def parse_m3u(lines: list[str]) -> list[dict]:
    # #EXTINF:387,Teremtes-konyve-01
    # otestamentum\01_teremtes\teremtes-konyve-01.mp3
    items = []
    pending_sec = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            pending_sec = int(line.split(":", 1)[1].split(",", 1)[0])
            continue
        if line.lower().endswith(".mp3"):
            rel = line.replace("\\", "/")
            items.append({"relative_path": rel, "extinf_sec": pending_sec})
            pending_sec = None
    return items
```

### Pattern 2: Safe resume + retry download
**What:** Download to `*.part`, retry transient failures, then atomic rename on success. [CITED: httpx + tenacity docs]
**When to use:** Every MP3 fetch.
**Example:**
```python
# Source: https://www.python-httpx.org/advanced/clients/
# Source: https://tenacity.readthedocs.io/en/latest/
@retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, max=30), reraise=True)
def download_with_resume(client: httpx.Client, url: str, dest: Path) -> None:
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with client.stream("GET", url, headers=headers) as r:
        r.raise_for_status()
        mode = "ab" if (have and r.status_code == 206) else "wb"
        with open(part, mode) as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    part.replace(dest)
```

### Pattern 3: Convert and assert invariants
**What:** Run ffmpeg and immediately validate with ffprobe JSON. [CITED: ffmpeg/ffprobe docs]
**When to use:** Every MP3→WAV conversion.
**Example:**
```bash
# Source: https://ffmpeg.org/ffmpeg.html
ffmpeg -y -i "in.mp3" -ac 1 -ar 16000 -c:a pcm_s16le "out.wav"

# Source: https://ffmpeg.org/ffprobe.html
ffprobe -v error -show_streams -show_format -print_format json "out.wav"
```

### Anti-Patterns to Avoid
- **Direct HTML scraping for canonical chapter list:** use M3U first, HTML only as fallback diagnostics. [VERIFIED: MEK index + m3u]
- **Trusting output file presence without probe:** a `.wav` file can exist but be truncated/corrupt; enforce probe checks. [VERIFIED: local partial-file decode warning]
- **Hard-failing all-bible run on source mismatch:** report missing/extra chapters per book, continue by default. [VERIFIED: EST/DAN/MAL mismatch runtime]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry/backoff | Custom loops with `sleep()` and counters | Tenacity policies | Cleaner, testable retry semantics and hooks. [CITED: tenacity docs] |
| HTTP pooling | Recreating socket per request manually | `httpx.Client` | Built-in connection reuse/timeouts/limits. [CITED: httpx clients/timeouts docs] |
| Audio decoding/resample | Custom MP3 decode pipeline in Python | ffmpeg CLI | Mature codec handling and deterministic conversion flags. [CITED: ffmpeg docs] |
| Stream metadata parser | Hand parser over binary MP3 headers | ffprobe JSON output | Reliable machine-readable output with stream fields. [CITED: ffprobe docs] |

**Key insight:** The risky parts of this phase are source variability and IO reliability, not algorithm novelty. Use battle-tested tools, keep custom code focused on manifest reconciliation + idempotent orchestration. [VERIFIED: runtime/source audit]

## Common Pitfalls

### Pitfall 1: Assuming versification chapter counts == available audio files
**What goes wrong:** `--all` failures when source has different chapter granularity.  
**Why it happens:** MEK playlist currently yields 1328 tracks, while local versification totals 1333 chapters. [VERIFIED: runtime count]  
**How to avoid:** Treat audio inventory as source-of-truth for downloadable tracks and emit discrepancy report (`missing`, `extra`).  
**Warning signs:** EST(16 vs 10), DAN(12 vs 14), MAL(4 vs 3) mismatches. [VERIFIED: runtime diff]

### Pitfall 2: Resume corruption from naive append logic
**What goes wrong:** Appending to files when server returns full body (`200`) instead of partial (`206`) can duplicate bytes. [ASSUMED]  
**Why it happens:** Range support or proxy behavior not validated per request.  
**How to avoid:** Append only if `status_code == 206`; otherwise overwrite `.part`.  
**Warning signs:** Output size larger than expected or decode warnings.

### Pitfall 3: Silent conversion drift due to unverified output format
**What goes wrong:** Downstream aligner receives wrong sample rate/channels.  
**Why it happens:** Conversion command succeeds but format assumptions are not checked.  
**How to avoid:** Enforce probe assertions after every conversion: `codec_name=pcm_s16le`, `sample_rate=16000`, `channels=1`. [VERIFIED: ffprobe JSON example]
**Warning signs:** Unexpected sample counts or alignment quality degradation.

### Pitfall 4: Trusting MP3 timestamps as sample-accurate boundaries
**What goes wrong:** Boundary offsets accumulate for long chapters in alignment workflows. [ASSUMED]  
**Why it happens:** Compressed stream frame/timebase behavior differs from raw PCM indexing. [ASSUMED]  
**How to avoid:** Seek only in WAV for alignment and store sample-based offsets. [ASSUMED]  
**Warning signs:** End-of-chapter drift compared to manual spot checks.

## Code Examples

### Concurrency + pooled client defaults
```python
# Source: https://www.python-httpx.org/advanced/clients/
# Source: https://www.python-httpx.org/advanced/timeouts/
limits = httpx.Limits(max_connections=12, max_keepalive_connections=6)
timeout = httpx.Timeout(20.0, connect=30.0, read=20.0, write=20.0, pool=10.0)

with httpx.Client(timeout=timeout, limits=limits, follow_redirects=True) as client:
    ...
```

### Rich progress for `audio download --all`
```python
# Source: https://context7.com/textualize/rich/llms.txt
with Progress(
    SpinnerColumn(),
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
    DownloadColumn(),
    TransferSpeedColumn(),
) as progress:
    task_id = progress.add_task("Downloading audio", total=total_bytes)
    ...
```

### ffprobe metadata extraction command
```bash
# Source: https://ffmpeg.org/ffprobe.html
ffprobe -v error -show_streams -show_format -print_format json "data/prepared/audio/GEN/001.wav"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One-off `curl` per file with no pooled client | Structured client pooling + timeout classes | Established in modern HTTPX docs | Better throughput and deterministic timeout behavior. [CITED: httpx clients/timeouts docs] |
| Ad hoc retry loops | Policy-driven retry (`stop`, `wait`, `retry`) | Tenacity standard usage | Fewer hidden retry bugs, better observability hooks. [CITED: tenacity docs] |
| Metadata from shell text parsing | ffprobe JSON parse | Standardized for machine output | Less brittle and easier test assertions. [CITED: ffprobe docs] |

**Deprecated/outdated:**
- Parsing MEK HTML as primary chapter source is outdated for this phase; M3U is cleaner and already track-oriented. [VERIFIED: MEK index + m3u]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | WAV-only seeking materially reduces timestamp drift vs MP3 seeking in this pipeline | Common Pitfalls / Phase req support | May over-prioritize conversion if drift is negligible in actual decoder path |
| A2 | Sample-based seek index sidecar is required (not optional) for Phase 3 acceptance | Requirements mapping / architecture | Could add unnecessary complexity if downstream can derive on-the-fly |
| A3 | Resume corruption risk from mixed `200`/`206` behavior is significant on this host path | Pitfalls | Might over-engineer resume logic |

## Open Questions (RESOLVED)

1. **EST/DAN chapter-structure mismatches for downstream alignment**
   - Decision: Phase 3 will emit an explicit inventory discrepancy artifact (`missing_vs_schema`, `extra_vs_schema`) and keep the downloader source-truth to MEK availability. No versification remap is performed in Phase 3.
   - Follow-through: Phase 4 planning must consume this artifact and decide mapping/reconciliation rules before alignment scoring.

2. **ffmpeg/ffprobe requirement policy**
   - Decision: `ffmpeg` and `ffprobe` are required runtime dependencies for Phase 3 command success (download/convert/info/prepare paths). No pure-Python fallback for conversion.
   - Follow-through: `audio info` may optionally use mutagen for a best-effort metadata fallback in the future, but current phase acceptance criteria remain ffprobe-based.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (uv runtime) | CLI commands | ✓ | 3.13.1 via `uv run` | — |
| uv | Dependency + command execution | ✓ | 0.5.27 | — |
| go-task/task | Taskfile targets | ✓ | 3.48.0 | direct `uv run` commands |
| ffmpeg | MP3→WAV conversion (AUD-03) | ✓ | 7.1.4 | none (blocking for AUD-03) |
| ffprobe | Metadata + format verification (AUD-03/04) | ✓ | 7.1.4 | mutagen metadata fallback (partial) |
| curl | Debug/manual source checks | ✓ | 8.15.0 | httpx programmatic checks |

**Missing dependencies with no fallback:** None on this machine. [VERIFIED: environment audit]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (dev dependency) [VERIFIED: PyPI query + codebase] |
| Config file | none explicit; pytest invoked from Taskfile [VERIFIED: Taskfile.yml] |
| Quick run command | `uv run pytest tests/ -x -v` |
| Full suite command | `uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUD-01 | Single chapter download retries and resumes | integration | `uv run pytest tests/test_audio_downloader.py::test_resume_after_partial -x` | ❌ Wave 0 |
| AUD-02 | `--all` parallel download honors max workers | integration | `uv run pytest tests/test_audio_downloader.py::test_parallel_worker_limit -x` | ❌ Wave 0 |
| AUD-03 | Converted WAV is 16kHz mono PCM | integration | `uv run pytest tests/test_audio_convert.py::test_wav_format_assertions -x` | ❌ Wave 0 |
| AUD-04 | `audio info` returns duration/bitrate/sample_rate | unit | `uv run pytest tests/test_audio_metadata.py::test_info_fields_present -x` | ❌ Wave 0 |
| AUD-05 | Seek index math uses sample-accurate offsets | unit | `uv run pytest tests/test_audio_seek_index.py::test_sample_offset_roundtrip -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -v`
- **Per wave merge:** `uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing`
- **Phase gate:** run all new audio tests + smoke command trio:
  - `uv run bibliavox audio download --book GEN --chapter 1`
  - `uv run bibliavox audio convert --book GEN --chapter 1`
  - `uv run bibliavox audio info --book GEN --chapter 1`

### Wave 0 Gaps
- [ ] `tests/test_audio_discovery.py` — M3U parsing, EXTINF extraction, path normalization
- [ ] `tests/test_audio_downloader.py` — retry, resume, HTTP 200/206 behavior
- [ ] `tests/test_audio_convert.py` — ffmpeg command contract + probe validation
- [ ] `tests/test_audio_metadata.py` — ffprobe JSON parsing and CLI formatting
- [ ] `tests/test_audio_cli.py` — Typer command flags (`--book/--chapter/--all/--workers`)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (public source download) [VERIFIED: MEK public URLs] |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Local CLI tool, no multi-user auth boundary [ASSUMED] |
| V5 Input Validation | yes | Validate `--book` against known USX set, chapter bounds against manifest/schema, and sanitize path joins. [VERIFIED: existing lookup patterns + reference data] |
| V6 Cryptography | no | No custom crypto needed in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via crafted manifest path | Tampering | Normalize + reject `..`, absolute paths, and separator escapes before file writes. [ASSUMED] |
| Untrusted media payload corruption | Tampering | Require ffprobe parse success and strict audio invariants before accepting conversion. [CITED: ffprobe docs] |
| Resource exhaustion on bulk download | DoS | Worker limits, timeout caps, retry caps, and skip-existing idempotency. [CITED: httpx timeout/limits docs] |

## Sources

### Primary (HIGH confidence)
- `https://mek.oszk.hu/08800/08820/mp3/biblia.m3u` — chapter inventory + `#EXTINF` durations, path conventions. [VERIFIED: webfetch + runtime parse]
- `https://mek.oszk.hu/08800/08820/mp3/index.html` — source listing confirms MP3 publication model. [VERIFIED: webfetch]
- `https://mek.oszk.hu/08800/08820/cedula.html` — catalog metadata for source edition. [VERIFIED: webfetch]
- `https://www.python-httpx.org/advanced/clients/` — client pooling and usage model. [CITED]
- `https://www.python-httpx.org/advanced/timeouts/` — timeout model (connect/read/write/pool). [CITED]
- `https://tenacity.readthedocs.io/en/latest/` — retry policy primitives and examples. [CITED]
- `https://ffmpeg.org/ffmpeg.html` and `https://ffmpeg.org/ffprobe.html` — conversion/probe command references. [CITED]
- `https://mutagen.readthedocs.io/en/latest/user/gettingstarted.html` — optional metadata fallback usage. [CITED]
- Local codebase files: `pyproject.toml`, `Taskfile.yml`, `bibliavox/main.py`, `bibliavox/cli/text.py`, `data/reference/versification.json`. [VERIFIED: codebase]
- Runtime checks executed in this session: m3u inventory scripts, versification diff script, tool availability/version probes, sample conversion/probe command. [VERIFIED: runtime]

### Secondary (MEDIUM confidence)
- Context7 CLI extracts for `/encode/httpx`, `/textualize/rich`, `/fastapi/typer` used to cross-check official patterns. [VERIFIED: ctx7 CLI output]

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — based on current project deps + official docs + runtime availability.
- Architecture: **HIGH** — directly mapped from phase requirements and existing project command patterns.
- Pitfalls: **MEDIUM** — major source mismatch pitfalls are verified; MP3 drift/range-edge behavior partially assumption-driven.

**Research date:** 2026-05-29  
**Valid until:** 2026-06-28
