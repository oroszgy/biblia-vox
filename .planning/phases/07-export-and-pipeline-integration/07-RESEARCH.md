# Phase 7: Export & Pipeline Integration - Research

**Researched:** 2026-06-02
**Domain:** JSONL export, pipeline orchestration, idempotent task chaining
**Confidence:** HIGH

## Summary

Phase 7 converts alignment results (already stored as per-chapter matched JSON in `data/evaluation/`) into a standardized JSONL export format, and wires all pipeline stages into a single end-to-end command. The evaluation engine from Phase 6 (`bibliavox/align/evaluate.py`) already produces per-chapter JSON with verse-level timestamps, canonical/matched text, and WER/CER metrics. The export layer reads these artifacts plus the canonical text corpus (`mek.jsonl`) to produce flat JSONL rows with the full field set specified in D-01 through D-07.

The pipeline orchestration uses chained Taskfile targets (D-08) with fail-fast behavior (D-09). Idempotency is achieved by checking whether export JSONL files already exist and have complete non-null timestamps (D-13). Rich progress bars follow the established pattern from `bibliavox/cli/align.py`.

**Primary recommendation:** Create a new `bibliavox/export/` package with a `writer.py` module for JSONL generation, and a `bibliavox/cli/export.py` CLI subcommand group. Wire pipeline stages as chained Taskfile targets with `deps` for ordering.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Flat rows, one per verse-model pair. Each JSONL line represents a single verse aligned by a single model.
- **D-02:** verse_ref format: "BOOK CH:VS" (e.g., "TIT 1:1"). Matches existing evaluation output convention.
- **D-03:** audio_file as canonical prepared path: `data/prepared/audio/{USX}/{chapter:03d}.wav`. Matches existing pipeline convention.
- **D-04:** Include both `canonical_text` (from source corpus) and `matched_text` (from transcription) fields.
- **D-05:** Include per-verse `wer` and `cer` metrics in each row.
- **D-06:** Export ALL verses including failed alignments. Failed verses have `null` timestamps and `0` confidence. No data loss.
- **D-07:** Fields per line: `verse_ref`, `audio_file`, `start_sec`, `end_sec`, `source` (model ID), `translation` ("SZIT"), `confidence` (0-1), `canonical_text`, `matched_text`, `wer`, `cer`.
- **D-08:** Chained Taskfile targets: `export:fetch-text`, `export:prepare-audio`, `export:align`, `export:jsonl`. Pipeline target `export:run` calls them in order.
- **D-09:** Fail-fast on model failure. Stop pipeline on first failure.
- **D-10:** Default model: VibeVoice only (`microsoft/VibeVoice-ASR-HF`). User can override via `MODEL=...` Taskfile variable or `--model` CLI flag.
- **D-11:** Per-stage Rich progress bars showing stage name, chapter count, and ETA. One bar per pipeline stage.
- **D-12:** Gold chapters defined via `BIBLIAVOX_GOLD_CHAPTERS` config setting in `bibliavox/config.py`. Default: TIT 1-3, TOB 1-4, ZEP 1-3 (10 chapters). User overrides via `.env` or env var.
- **D-13:** Chapter "completed" = export JSONL file exists AND all verses have non-null timestamps for the selected model. Thorough check prevents partial exports.
- **D-14:** `--force` flag triggers full re-run of ALL stages for forced chapters. Guarantees fresh data.
- **D-15:** Normalize all confidence scores to 0-1 range per model using divide-by-max method. RapidFuzz 0-100 → divide by 100.
- **D-16:** Normalization applied during export, not during alignment. Raw scores preserved in alignment cache.
- **D-17:** Use `mek.jsonl` (35,350 verses, 73 books) as canonical text source for export.

### OpenCode's Discretion
- Specific structure of the export module (new `bibliavox/export/` package or extend `bibliavox/align/`)
- Whether to include a `bibliavox export` CLI subcommand group or wire export into existing `bibliavox align`
- How to handle the Taskfile variable passing for gold chapters config

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | JSONL output format: `{verse_ref, audio_file, start_sec, end_sec, source, translation, confidence}` | Export writer module reads evaluation matched JSON + mek.jsonl, transforms to flat rows with D-07 fields. Confidence normalized via D-15 divide-by-max. |
| EXP-02 | Typer sub-commands: `text`, `audio`, `align`, `export`, `backup` | New `bibliavox/cli/export.py` with `export` subcommand group registered in `main.py`. Pattern identical to existing `cli/align.py`. |
| EXP-03 | Taskfile targets for each pipeline stage (download-text, download-audio, parse, align, export, backup) | Chained Taskfile targets with `deps` for ordering. Pattern exists in `audio:prepare` → `audio:download` chain. |
| EXP-04 | Rich progress display with stage indicators and ETA | Rich Progress bar pattern from `rich.progress` with custom task descriptions per stage. |
| EXP-05 | Pipeline runs end-to-end on gold subset chapters only (configurable chapter list) | `BIBLIAVOX_GOLD_CHAPTERS` config in `config.py`. Idempotency via D-13 existence check. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JSONL export generation | API / Backend | — | Pure data transformation, no UI or external service |
| Pipeline orchestration | API / Backend | — | Taskfile chaining + CLI orchestration |
| Progress display | Browser / Client | — | Rich terminal output, user-facing |
| Gold chapter config | API / Backend | — | Pydantic Settings, env var driven |
| Idempotency checks | API / Backend | — | Filesystem state inspection |
| Confidence normalization | API / Backend | — | Math transformation during export |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | >=0.26 | CLI subcommand groups | Already used throughout project [VERIFIED: pyproject.toml] |
| rich | (latest) | Progress bars, tables, console output | Already used throughout project [VERIFIED: pyproject.toml] |
| pydantic-settings | (latest) | Configuration management | Already used for BIBLIAVOX_ settings [VERIFIED: config.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | — | JSONL line-by-line writing | Always — no external library needed [VERIFIED: existing pattern in evaluate.py] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| json (stdlib) | jsonlines library | Unnecessary dependency — `json.dumps()` per line is the established pattern per D-[2.5] decision |

**Installation:** No new dependencies needed. All required libraries are already in `pyproject.toml`.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │              Pipeline Orchestration              │
                    │         (Taskfile chained targets)               │
                    └──────┬──────────┬──────────┬──────────┬─────────┘
                           │          │          │          │
                    ┌──────▼──┐ ┌─────▼────┐ ┌──▼───────┐ ┌▼──────────┐
                    │  Text   │ │  Audio   │ │ Alignment│ │  Export   │
                    │  Fetch  │ │  Prepare │ │  (model) │ │  JSONL    │
                    │ (Phase2)│ │ (Phase3) │ │ (Ph4-6)  │ │ (Phase7)  │
                    └────┬────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘
                         │           │            │              │
                    ┌────▼───────────▼────────────▼──────────────▼────┐
                    │              data/ directory                     │
                    │  processed/text/mek.jsonl  ← canonical text     │
                    │  prepared/audio/{USX}/     ← WAV files          │
                    │  evaluation/*_matched.json ← alignment results  │
                    │  export/*.jsonl            ← FINAL OUTPUT       │
                    └─────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
bibliavox/
├── export/                 # NEW: Export package
│   ├── __init__.py
│   └── writer.py           # JSONL generation from evaluation data
├── cli/
│   ├── export.py           # NEW: Export CLI subcommand group
│   └── ...existing...
├── config.py               # MODIFIED: Add BIBLIAVOX_GOLD_CHAPTERS
└── main.py                 # MODIFIED: Register export_app
```

### Pattern 1: JSONL Export Writer

**What:** Read per-chapter matched JSON from `data/evaluation/`, join with canonical text from `mek.jsonl`, normalize confidence, write flat JSONL rows.

**When to use:** When user runs `bibliavox export jsonl` or `task export:jsonl`.

**Example:**
```python
# Source: Pattern from bibliavox/align/evaluate.py save_evaluation_report()
import json
from pathlib import Path

def export_chapter_jsonl(
    matched_path: Path,
    audio_file: str,
    translation: str,
    output_file: Path,
) -> int:
    """Export a single chapter's matched results to JSONL format.
    
    Returns number of verses written.
    """
    with open(matched_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    model = data["model"]
    chapter = data["chapter"]  # e.g., "TIT 1"
    book, ch_num = chapter.split()
    
    # Normalize confidence: divide-by-max (D-15)
    verses = data["verses"]
    max_conf = max((v.get("confidence_score", 0) for v in verses), default=1.0)
    if max_conf == 0:
        max_conf = 1.0
    
    lines_written = 0
    with open(output_file, "a", encoding="utf-8") as out:
        for v in verses:
            # D-02: verse_ref format "BOOK CH:VS"
            verse_ref = f"{book} {ch_num}:{v['verse_id']}"
            
            # D-15: Normalize confidence to 0-1
            raw_conf = v.get("confidence_score", 0)
            confidence = round(raw_conf / max_conf, 4)
            
            # D-05: Compute per-verse WER/CER
            canonical = v.get("canonical_text", "")
            matched_text = v.get("matched_text", "")
            wer = compute_wer(canonical, matched_text) if canonical else 0.0
            cer = compute_cer(canonical, matched_text) if canonical else 0.0
            
            row = {
                "verse_ref": verse_ref,
                "audio_file": audio_file,
                "start_sec": v.get("start_sec"),      # null for failed
                "end_sec": v.get("end_sec"),            # null for failed
                "source": model,
                "translation": translation,
                "confidence": confidence,
                "canonical_text": canonical,
                "matched_text": matched_text,
                "wer": round(wer, 4),
                "cer": round(cer, 4),
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            lines_written += 1
    
    return lines_written
```

### Pattern 2: Pipeline Orchestration via Taskfile Chaining

**What:** Chain existing Taskfile targets using `deps` to create end-to-end pipeline.

**When to use:** When user runs `task export:run --gold`.

**Example:**
```yaml
# Source: Pattern from audio:prepare → audio:download chain
export:run:
  desc: Run full pipeline on gold chapters (text → audio → align → export)
  cmds:
    - task: export:jsonl
      vars:
        GOLD: "true"
        MODEL: "{{.MODEL}}"
        FORCE: "{{.FORCE}}"
  deps:
    - export:align
```

### Pattern 3: Idempotency Check

**What:** Skip chapters that already have complete export output unless `--force` is passed.

**When to use:** Before processing each chapter in the export pipeline.

**Example:**
```python
def is_chapter_complete(export_path: Path, model: str) -> bool:
    """Check if chapter export is complete per D-13.
    
    Complete = file exists AND all verses have non-null timestamps for model.
    """
    if not export_path.exists():
        return False
    
    with open(export_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("source") == model:
                if row.get("start_sec") is None or row.get("end_sec") is None:
                    return False
    return True
```

### Anti-Patterns to Avoid

- **Single monolithic CLI command:** Don't build one `bibliavox pipeline run` command that does everything. Use Taskfile chaining (D-08) — each stage is independently runnable and testable.
- **Export during alignment:** Don't modify alignment code to produce JSONL directly. Keep alignment output as-is (raw scores preserved per D-16) and transform during export.
- **Hardcoded gold chapters in multiple places:** Define `BIBLIAVOX_GOLD_CHAPTERS` once in `config.py` (D-12), reference from both CLI and Taskfile.
- **Using jsonlines library:** The project uses `json.dumps()` per line everywhere (established pattern from Phase 2.5). Don't introduce a new dependency.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bars | Custom ANSI escape codes | `rich.progress.Progress` | Already a project dependency, handles terminal width, ETA |
| JSONL writing | Custom serialization | `json.dumps()` per line | Established pattern, stdlib, no dependency |
| Config management | Custom env parsing | `pydantic_settings.BaseSettings` | Already used in `config.py`, handles .env files |
| Taskfile chaining | Shell scripts with `&&` | Taskfile `deps` | go-task handles dependency ordering, parallelism, status checks |

**Key insight:** Phase 7 is primarily a wiring/integration phase. The core logic (alignment, metrics, text loading) already exists. The export layer is a thin transformation on top of existing evaluation artifacts.

## Common Pitfalls

### Pitfall 1: Confidence Score Range Mismatch
**What goes wrong:** Different models produce confidence scores in different ranges (RapidFuzz: 0-100, VibeVoice: 0-100, MMS_FA: 0-1). Exported JSONL has inconsistent confidence values.
**Why it happens:** Raw scores are model-specific; normalization wasn't applied during alignment (D-16).
**How to avoid:** Apply divide-by-max normalization per model during export (D-15). Compute max from the batch being exported.
**Warning signs:** Confidence values >1.0 in output, or all values near 0 for one model.

### Pitfall 2: Missing Verses in Export
**What goes wrong:** Some verses from canonical text don't appear in export because alignment failed silently.
**Why it happens:** Alignment code skips chapters on error (fail-fast per D-09), but export only reads what exists.
**How to avoid:** D-06 requires exporting ALL verses. Export must join against canonical text (`mek.jsonl`) and emit rows with `null` timestamps for missing verses.
**Warning signs:** Export line count < canonical verse count for a chapter.

### Pitfall 3: Idempotency Check Too Lenient
**What goes wrong:** Partial exports (some verses aligned, some not) are treated as complete, skipping re-processing.
**Why it happens:** Only checking file existence, not content completeness.
**How to avoid:** D-13 requires checking that ALL verses have non-null timestamps for the selected model.
**Warning signs:** Re-running pipeline produces same incomplete output.

### Pitfall 4: Taskfile Variable Passing
**What goes wrong:** `task export:run --gold` doesn't pass the `--gold` flag to sub-tasks.
**Why it happens:** go-task parses task-level flags itself; command flags aren't supported (documented in Taskfile.yml comment at line 120-122).
**How to avoid:** Use Taskfile variable syntax: `task export:run GOLD=true MODEL=vibevoice`. This is the established pattern from Phase 3 (D-34 decision).
**Warning signs:** Flags silently ignored, pipeline runs on wrong chapters.

### Pitfall 5: Evaluation Data Not Yet Generated
**What goes wrong:** Export tries to read `data/evaluation/*_matched.json` but files don't exist because alignment hasn't been run.
**Why it happens:** Phase 7 depends on Phase 6 output, but user may not have run alignment yet.
**How to avoid:** Pipeline target `export:align` should trigger alignment if needed. Check for evaluation data before export and provide clear error message.
**Warning signs:** FileNotFoundError or empty export output.

## Code Examples

### Registering Export CLI in main.py

```python
# Source: Existing pattern in bibliavox/main.py
from bibliavox.cli.export import app as export_app

app.add_typer(export_app, name="export", help="Export alignment results")
```

### Rich Progress Bar with Stage Indicators

```python
# Source: rich.progress documentation
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeRemainingColumn(),
    console=console,
) as progress:
    task = progress.add_task("Exporting chapters...", total=len(chapters))
    for chapter in chapters:
        # ... process chapter ...
        progress.advance(task)
```

### Loading Gold Chapters from Config

```python
# Source: Pattern from bibliavox/config.py
# Add to BibliavoxSettings:
gold_chapters: str = "TIT 1,TIT 2,TIT 3,TOB 1,TOB 2,TOB 3,TOB 4,ZEP 1,ZEP 2,ZEP 3"
"""Comma-separated list of BOOK CHAPTER pairs for gold subset. Override via BIBLIAVOX_GOLD_CHAPTERS."""

def parse_gold_chapters(raw: str) -> list[tuple[str, int]]:
    """Parse "TIT 1,TIT 2,..." into [("TIT", 1), ("TIT", 2), ...]"""
    chapters = []
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid gold chapter format: {pair!r}. Expected 'BOOK CHAPTER'.")
        chapters.append((parts[0], int(parts[1])))
    return chapters
```

### Writing JSONL with json.dumps (Established Pattern)

```python
# Source: bibliavox/align/evaluate.py save_evaluation_report()
import json

with open(output_path, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SZIT text source (66 books) | MEK text source (73 books) | Phase 2.6 | Export uses mek.jsonl as canonical source (D-17) |
| Hardcoded gold chapters in CLI | BIBLIAVOX_GOLD_CHAPTERS config | Phase 7 (this phase) | Configurable via .env or env var |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Confidence normalization via divide-by-max is sufficient for v1 calibration | Confidence Normalization | May need percentile-based or model-specific normalization in v2 |
| A2 | `data/evaluation/*_matched.json` files will exist when export runs (Phase 6 completed) | Integration Points | Pipeline must handle missing evaluation data gracefully |
| A3 | All 4 models in gauntlet produce compatible verse structures (verse_id, start_sec, end_sec, confidence_score) | Export Writer | May need per-model adapters if structure differs |

## Open Questions

1. **Should export CLI be a new subcommand group or extend `bibliavox align`?**
   - What we know: CONTEXT.md says "OpenCode's Discretion"
   - What's unclear: Whether `bibliavox export` is cleaner than `bibliavox align export`
   - Recommendation: New `bibliavox export` subcommand group — export is conceptually distinct from alignment, and the ROADMAP lists it as a separate requirement category (EXP-xx)

2. **How to handle the pipeline `export:align` stage — does it re-run alignment or just verify it exists?**
   - What we know: D-14 says `--force` triggers full re-run. D-13 checks for existing complete output.
   - What's unclear: Whether `export:align` should be a passthrough check or actually invoke Docker alignment
   - Recommendation: `export:align` checks for evaluation data existence. If missing, runs `align:evaluate-gold` (which requires Docker). If present and not `--force`, skips.

3. **Should the export pipeline target be `export:run` or `pipeline:run`?**
   - What we know: Success criteria says `task pipeline:run --gold`. D-08 says `export:run`.
   - What's unclear: Whether to use `pipeline:` namespace or `export:` namespace
   - Recommendation: Use `export:run` per D-08 (locked decision). The success criteria text may need updating to match.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13+ | All modules | ✓ | 3.13+ | — |
| uv | Package management | ✓ | — | — |
| go-task (task) | Taskfile targets | ✓ | — | — |
| Docker | GPU alignment stages | ✓ | — | Skip alignment, use cached results |
| rich | Progress bars | ✓ | (in pyproject.toml) | — |
| typer | CLI framework | ✓ | (in pyproject.toml) | — |

**Missing dependencies with no fallback:** None — all required tools are available.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (in pyproject.toml dev dependencies) |
| Config file | none — uses default pytest discovery |
| Quick run command | `uv run pytest tests/ -x -v` |
| Full suite command | `uv run pytest tests/ -x -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 | JSONL output has all D-07 fields | unit | `uv run pytest tests/test_export_writer.py -x` | ❌ Wave 0 |
| EXP-01 | Failed verses have null timestamps | unit | `uv run pytest tests/test_export_writer.py::test_null_timestamps -x` | ❌ Wave 0 |
| EXP-01 | Confidence normalized to 0-1 | unit | `uv run pytest tests/test_export_writer.py::test_confidence_normalize -x` | ❌ Wave 0 |
| EXP-02 | `bibliavox export --help` shows subcommands | smoke | `uv run bibliavox export --help` | ❌ Wave 0 |
| EXP-04 | Progress bars display during export | manual | Visual inspection | Manual only |
| EXP-05 | Gold chapters from config | unit | `uv run pytest tests/test_config.py::test_gold_chapters -x` | ❌ Wave 0 |
| EXP-05 | Idempotency skips complete chapters | unit | `uv run pytest tests/test_export_writer.py::test_idempotency -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_export*.py tests/test_config.py -x`
- **Per wave merge:** `uv run pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_export_writer.py` — covers EXP-01 JSONL generation, null handling, confidence normalization
- [ ] `tests/test_export_cli.py` — covers EXP-02 CLI smoke tests
- [ ] `tests/test_config.py` — covers EXP-05 gold chapter parsing (may already exist from Phase 1)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth in CLI tool |
| V3 Session Management | no | Stateless pipeline |
| V4 Access Control | no | Local filesystem only |
| V5 Input Validation | yes | Validate gold chapter format, model names, file paths |
| V6 Cryptography | no | No secrets in export |

### Known Threat Patterns for CLI + JSONL

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----|
| Path traversal in audio_file field | Tampering | Validate paths are under data/prepared/ |
| Malformed JSONL injection | Tampering | json.dumps with ensure_ascii=False (stdlib handles escaping) |
| Config injection via env vars | Elevation of Privilege | pydantic-settings validates types |

## Sources

### Primary (HIGH confidence)
- `bibliavox/align/evaluate.py` — WER/CER computation, JSONL save pattern, Rich table builder
- `bibliavox/cli/align.py` — CLI pattern with Rich output, gold chapter handling, model selection
- `bibliavox/config.py` — Pydantic Settings pattern, BIBLIAVOX_ prefix
- `Taskfile.yml` — Task chaining pattern, variable syntax
- `data/evaluation/TIT_001_microsoft_VibeVoice-ASR-HF_matched.json` — Actual data structure
- `data/processed/text/mek.jsonl` — Canonical text format

### Secondary (MEDIUM confidence)
- CONTEXT.md D-01 through D-17 — Locked design decisions

### Tertiary (LOW confidence)
- Assumptions A1-A3 — Confidence normalization approach, data availability, model compatibility

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture: HIGH — patterns established in prior phases, evaluation engine is the foundation
- Pitfalls: HIGH — identified from existing code patterns and known Taskfile behavior

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable — depends on completed Phase 6 output format)
