# Phase 1: Foundation & Versification Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 1-Foundation & Versification Schema
**Areas discussed:** Data sourcing, Project structure, CLI initial shape, Configuration approach

---

## Data Sourcing

### Versification schema storage

| Option | Description | Selected |
|--------|-------------|----------|
| Static JSON in package | Generate a JSON file from szentiras.eu data once, embed it in the Python package. Fast, offline, no network dependency. Update manually when needed. | ✓ |
| Fetch on first use | Download from szentiras.eu GitHub repo on first CLI run, cache locally. Always fresh but adds network dependency and startup latency. | |
| Fetch + cache with version check | Download on first use, check for updates periodically. Most complex but balances freshness and offline capability. | |

**User's choice:** Static JSON in package (Recommended)
**Notes:** No network dependency at runtime. Generated once from szentiras.eu data.

### Verse schema depth

| Option | Description | Selected |
|--------|-------------|----------|
| Book + chapter counts only | 73 books with names, abbreviations, USX codes, and chapter counts per book. Verse counts fetched/validated at runtime from szentiras.eu API during Phase 2. | |
| Full verse schema | 73 books + all chapter/verse counts (e.g., GEN has 50 chapters, GEN 1 has 31 verses). More self-contained but requires building the full schema now from tdverse data. | ✓ |

**User's choice:** Full verse schema
**Notes:** Self-contained reference data. No runtime fetching needed.

---

## Project Structure

### Project layout

| Option | Description | Selected |
|--------|-------------|----------|
| src-layout with modules | src/bibliavox/ as package root, submodules per pipeline stage (reference/, text/, audio/, align/, export/, cli/). Standard for Python packages with CLI. | |
| Flat layout | bibliavox/ at repo root. Simpler but less conventional for publishable packages. | ✓ |

**User's choice:** Flat layout
**Notes:** Simpler for this CLI tool.

### Reference data location

| Option | Description | Selected |
|--------|-------------|----------|
| bibliavox/reference/data/ | Inside the package, next to the code that reads it. Reference module owns its data. | |
| data/reference/ at repo root | Outside the package. Easier to update without touching code, but requires path resolution logic. | ✓ |

**User's choice:** data/reference/ at repo root
**Notes:** Requires path resolution logic in config module.

---

## CLI Initial Shape

### CLI scope

| Option | Description | Selected |
|--------|-------------|----------|
| Help + versification lookup | bibliavox --help works, plus a 'reference' subcommand to list books, look up abbreviations, show chapter/verse counts. Demonstrates the data model. | ✓ |
| Help skeleton only | Just --help with subcommand groups stubbed (text, audio, align, export). Reference lookup added in Phase 2. | |
| Full subcommand stubs | All subcommands (text, audio, align, export, reference) with --help for each, but only reference actually works. | |

**User's choice:** Help + versification lookup (Recommended)
**Notes:** Demonstrates the data model from day 1.

### Taskfile targets

| Option | Description | Selected |
|--------|-------------|----------|
| dev tasks only | task lint, task format, task typecheck, task test. Development workflow targets. Pipeline targets added in later phases. | |
| dev + reference tasks | Dev tasks plus task reference:list, task reference:lookup. Demonstrates Taskfile-to-CLI integration pattern. | |

**User's choice:** dev tasks + reproducible reference data generation
**Notes:** User wants to be able to reproduce the reference data from source. Added reference:generate task.

---

## Configuration Approach

### Config library

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic Settings | Typed config with validation, .env file support, environment variable loading. Well-documented pattern, already in research recommendations. | ✓ |
| Simple dataclass + dotenv | stdlib dataclass with python-dotenv for .env loading. Fewer dependencies but no validation. | |
| Plain dict + os.environ | Minimal approach. No typing, no validation. Simplest but least safe. | |

**User's choice:** Pydantic Settings (Recommended)
**Notes:** Typed config with validation and .env support.

### Config values

| Option | Description | Selected |
|--------|-------------|----------|
| Paths + API key placeholder | data_dir, cache_dir, reference_data_path, plus szentiras_api_key (empty default). Model/audio settings added in later phases. | ✓ |
| Full config skeleton | All future settings pre-defined (model name, sample rate, concurrency, etc.) with sensible defaults. More upfront work but avoids config evolution. | |

**User's choice:** Paths + API key placeholder (Recommended)
**Notes:** Minimal config for Phase 1. Model/audio/concurrency settings added in later phases.

---

## OpenCode's Discretion

- Module nesting depth within `bibliavox/`
- Test framework choice (pytest recommended)
- How path resolution works for `data/reference/` (relative to repo root vs. env var override)
- Whether to include a `bibliavox/version.py` or rely on pyproject.toml

## Deferred Ideas

None — discussion stayed within phase scope
