# Phase 2: Text Acquisition & Validation - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Acquire the full Szent István Társulat Bible text from a structured JSON source (`peterpolgar/Biblia-json-xml`), normalize it through a reproducible two-stage pipeline, and validate verse counts against our versification schema. The output is a clean, normalized verse corpus in `data/processed/` ready for alignment work.

**Key change from roadmap:** The szentiras.eu API is not viable (requires API key from maintainers). Instead, a structured JSON source on GitHub (`H_Kaldi_SZIT.json`) provides the full SZIT Bible in dictionary format. The mek.oszk.hu HTML parser is deferred — SZIT JSON is the sole text source for v1.

</domain>

<decisions>
## Implementation Decisions

### Text Source
- **D-01:** Primary (and only) text source is `peterpolgar/Biblia-json-xml` repo, file `bibles_json_dict/full_bibles/H_Kaldi_SZIT.json`. Unlicense license. Structure: `{book_name: {chapter: {verse: "text"}}}` with English book names.
- **D-02:** Book name mapping available in `magyar_angol_konyvek_roviditesei.json` from same repo. Must map English book names to our USX codes.
- **D-03:** mek.oszk.hu HTML parser is **deferred** — not needed for v1. SZIT JSON is sufficient as sole source.
- **D-04:** szentiras.eu API is **dropped entirely** — not viable without API key from maintainers.

### Normalization Pipeline
- **D-05:** Two-stage normalization approach:
  1. **Stage 1 (lightweight):** Whitespace normalization, line ending standardization, NFC Unicode normalization
  2. **Stage 2 (schema matching):** Verify verse counts match versification schema; apply additional normalization only if needed
- **D-06:** All normalization steps recorded in Taskfile for reproducibility
- **D-07:** NFC Unicode normalization (composed form) — standard for web/API text, most Hungarian text already NFC

### Data Flow
- **D-08:** Raw source data stored at `data/raw/text/` (downloaded JSON from GitHub)
- **D-09:** Processed/normalized data stored at `data/processed/text/` (ready for alignment)
- **D-10:** All pipeline steps are reproducible — Taskfile targets for each stage, no manual intervention

### Validation
- **D-11:** Validate verse counts per chapter against our versification schema (from Phase 1)
- **D-12:** Discrepancy report in JSON format — structured records with book, chapter, verse, severity, details
- **D-13:** No cross-source text comparison for v1 (HTML parser deferred)

### OpenCode's Discretion
- How to handle the book name mapping (English names in JSON → USX codes)
- Whether to store intermediate normalized stages or only final output
- Error handling for missing books/chapters in the JSON source
- Whether to vendor the SZIT JSON file or fetch it from GitHub at build time

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Text Source
- `https://github.com/peterpolgar/Biblia-json-xml` — SZIT Bible structured JSON (Unlicense). Primary text source for Phase 2.
- `https://github.com/peterpolgar/Biblia-json-xml/blob/main/bibles_json_dict/full_bibles/H_Kaldi_SZIT.json` — The actual SZIT Bible JSON file
- `https://github.com/peterpolgar/Biblia-json-xml/blob/main/magyar_angol_konyvek_roviditesei.json` — Hungarian/English book name mapping

### Project Context
- `.planning/research/SUMMARY.md` — Stack recommendations, architecture approach, critical pitfalls
- `.planning/ROADMAP.md` §Phase 2 — Success criteria and requirement mappings
- `.planning/REQUIREMENTS.md` — TEXT-01, TEXT-02, TEXT-03, TEXT-05 requirement details

### Reference Data
- `data/reference/versification.json` — Verse counts per chapter for all 73 books (used for validation)
- `data/reference/books.json` — 73-book Catholic Bible catalog with USX codes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bibliavox/reference/schema.py` — BookSchema with chapter/verse counts, load_versification(), get_verse_count()
- `bibliavox/reference/books.py` — Book dataclass, lookup_by_usx_code(), lookup_by_abbreviation()
- `bibliavox/config.py` — BibliavoxSettings with data_dir, cache_dir, reference_data_path
- `bibliavox/cli/reference.py` — CLI pattern for sub-command groups (Pattern 4)

### Established Patterns
- Frozen dataclasses for immutable reference data (Book, BookSchema)
- Module-level caches with lazy loading
- Typer sub-command groups with Rich console output
- Taskfile targets for dev tasks (lint, format, typecheck, test)

### Integration Points
- `bibliavox/main.py` — Register new `text` subcommand group
- `Taskfile.yml` — Add text pipeline tasks (fetch, normalize, validate)
- `data/` directory structure — `data/raw/text/` and `data/processed/text/` need creation

</code_context>

<specifics>
## Specific Ideas

- User discovered the `peterpolgar/Biblia-json-xml` repo as a better alternative to the szentiras.eu API
- User wants a reproducible pipeline: all data processing steps recorded in Taskfile
- Two-stage normalization: lightweight first, then schema matching, then additional normalization only if needed
- Data stored in `data/raw/` and `data/processed/` folders
- JSON discrepancy reports for validation (machine-readable, not terminal output)

</specifics>

<deferred>
## Deferred Ideas

- **mek.oszk.hu HTML parser** — Deferred to future phase if cross-source validation becomes needed. Not required for v1 since SZIT JSON is sufficient.
- **Cross-source text comparison** — Validation against mek.oszk.hu HTML deferred. Only verse count validation against schema for v1.

</deferred>

---

*Phase: 2-Text Acquisition & Validation*
*Context gathered: 2026-05-29*
