# Phase 2: Text Acquisition & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 2-Text Acquisition & Validation
**Areas discussed:** Text Source, Normalization, Validation, HTML Parser

---

## Text Source (major pivot)

| Option | Description | Selected |
|--------|-------------|----------|
| szentiras.eu API | Structured JSON per verse, SZIT available, needs API key | |
| peterpolgar/Biblia-json-xml | GitHub repo with structured SZIT Bible JSON (Unlicense) | ✓ |
| mek.oszk.hu HTML | HTML scraping as primary/fallback | |

**User's choice:** Ignore the API strategy completely — it is not viable. Use `peterpolgar/Biblia-json-xml` repo instead.
**Notes:** User discovered this repo independently. The `H_Kaldi_SZIT.json` file contains the full SZIT Bible in JSON dictionary format. Unlicense license. This replaces the szentiras.eu API entirely.

---

## Normalization

| Option | Description | Selected |
|--------|-------------|----------|
| NFC (Recommended) | Unicode NFC normalization — standard for web/API text | ✓ |
| NFD | Unicode NFD normalization — decomposed form | |

**User's choice:** NFC (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Light cleanup only | Only strip extra whitespace and normalize line endings | |
| Aggressive normalization | Strip punctuation, normalize abbreviations, standardize quotes | |
| Keep original text untouched | Only normalize for comparison | |

**User's choice:** First have a lightweight normalization, then make sure we can match the schema, and if needed, have a second round of normalization.
**Notes:** All data processing steps should be recorded in the Taskfile. Data should be stored in `data/raw` and `data/processed` folders. The whole pipeline should be reproducible.

---

## Validation & Discrepancy Reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Verse count validation (Recommended) | Count verses per chapter, compare against versification schema | ✓ |
| Cross-source text comparison | Compare verse text between SZIT JSON and mek.oszk.hu HTML | |
| Both | Both verse counts AND text comparison | |

**User's choice:** Verse count validation (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| JSON report (Recommended) | Machine-readable structured discrepancy records | ✓ |
| Terminal table | Human-readable Rich table output | |
| Both JSON + terminal | Both formats | |

**User's choice:** JSON report (Recommended)

---

## HTML Parser

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal parser | Basic verse extraction for validation only | |
| Skip HTML parser for now | SZIT JSON is sufficient for v1 | ✓ |
| Full parser | Robust parser with retry, encoding detection | |

**User's choice:** Skip HTML parser for now.
**Notes:** SZIT JSON is the sole text source for v1. mek.oszk.hu HTML parser deferred to future phase if cross-source validation becomes needed.

---

## OpenCode's Discretion

- How to handle the book name mapping (English names in JSON → USX codes)
- Whether to store intermediate normalized stages or only final output
- Error handling for missing books/chapters in the JSON source
- Whether to vendor the SZIT JSON file or fetch it from GitHub at build time

## Deferred Ideas

- **mek.oszk.hu HTML parser** — Not needed for v1, add in future phase if cross-source validation required
- **Cross-source text comparison** — Only verse count validation against schema for v1
