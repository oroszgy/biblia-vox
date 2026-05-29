# Phase 1: Foundation & Versification Schema - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish project infrastructure: 73-book Catholic Bible versification schema (with full chapter/verse counts), project structure, CLI scaffolding with versification lookup, and configuration management. This phase produces the canonical reference data that every other phase depends on.

</domain>

<decisions>
## Implementation Decisions

### Data Sourcing
- **D-01:** Versification schema stored as static JSON embedded in the package. No network dependency at runtime. Generated once from szentiras.eu `tdverse` data, updated manually when needed.
- **D-02:** Full verse schema — include chapter counts per book AND verse counts per chapter (e.g., GEN has 50 chapters, GEN 1 has 31 verses). Self-contained, no runtime fetching needed for the reference data.
- **D-03:** Source data comes from szentiras.eu GitHub repo's `tdverse` schema (AGPL licensed). Build a generation script to produce the static JSON from this source.

### Project Structure
- **D-04:** Flat layout — `bibliavox/` at repo root (not src-layout). Simpler for this CLI tool.
- **D-05:** Reference data lives at `data/reference/` (repo root, outside the package). Requires path resolution logic in config module.
- **D-06:** Submodules per pipeline stage: `bibliavox/reference/`, `bibliavox/text/`, `bibliavox/audio/`, `bibliavox/align/`, `bibliavox/export/`, `bibliavox/cli/`. Only `reference/` and `cli/` are implemented in Phase 1.

### CLI Shape
- **D-07:** Phase 1 delivers `bibliavox --help` working plus a `reference` subcommand group with: `list` (all 73 books), `lookup <abbreviation>` (find book by Hungarian abbreviation), `info <book>` (show chapter/verse counts).
- **D-08:** Taskfile includes dev tasks (`lint`, `format`, `typecheck`, `test`) plus a `reference:generate` task that reproduces the static JSON from source data. Demonstrates Taskfile-to-CLI integration pattern.

### Configuration
- **D-09:** Pydantic Settings for typed config with validation and .env file support.
- **D-10:** Phase 1 config includes: `data_dir`, `cache_dir`, `reference_data_path`, `szentiras_api_key` (empty default). Model/audio/concurrency settings deferred to later phases.

### OpenCode's Discretion
- Module nesting depth within `bibliavox/`
- Test framework choice (pytest recommended)
- How path resolution works for `data/reference/` (relative to repo root vs. env var override)
- Whether to include a `bibliavox/version.py` or rely on pyproject.toml

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Versification Data
- `.planning/research/SUMMARY.md` — Stack recommendations, architecture approach, critical pitfalls
- `.planning/research/ARCHITECTURE.md` — Module structure, data flow, component boundaries
- `.planning/ROADMAP.md` §Phase 1 — Success criteria and requirement mappings
- `.planning/REQUIREMENTS.md` — TEXT-04, TEXT-06, INF-02 requirement details

### Project Setup
- `pyproject.toml` — Existing project config (Python 3.13+, uv, typer, ruff, ty)
- `AGENTS.md` — Key commands (uv sync, uv run, task --list, ruff, ty)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml` — Already initialized with Python 3.13+, uv, typer, ruff, ty dependencies
- `hello.py` — Placeholder only, can be removed or repurposed

### Established Patterns
- None yet — this is the foundation phase that establishes patterns for all subsequent phases

### Integration Points
- `pyproject.toml` defines the CLI entry point (typer app)
- `Taskfile.yml` will be created to define task targets
- `data/reference/` directory needs to be created for static JSON

</code_context>

<specifics>
## Specific Ideas

- User wants a reproducible way to generate the reference data from source (task reference:generate or similar)
- The `tdverse` schema from szentiras.eu uses `gepi` codes: `{bookNum}{chapter:3d}{verse:3d}00` — this encoding should be preserved in the reference data for downstream use

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 1-Foundation & Versification Schema*
*Context gathered: 2026-05-29*
