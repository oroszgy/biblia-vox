# Phase 2: Text Acquisition & Validation - Research

**Researched:** 2026-05-29
**Status:** Complete

## Text Source Analysis

### peterpolgar/Biblia-json-xml Repository

**URL:** https://github.com/peterpolgar/Biblia-json-xml
**License:** Unlicense (public domain)
**SZIT File:** `bibles_json_dict/full_bibles/H_Kaldi_SZIT.json`

**JSON Structure:**
```json
{
  "Genesis": {
    "1": {
      "1": "Kezdetben teremté Isten az eget és a földet.",
      "2": "A föld pedig kietlen és puszta vala...",
      ...
    },
    "2": { ... },
    ...
  },
  "Exodus": { ... },
  ...
}
```

**Key observations:**
- All keys are strings (chapter numbers, verse numbers as strings)
- Book names are in English (not Hungarian)
- Top-level keys are English book names
- Nested structure: book → chapter → verse → text

### Book Name Mapping

**File:** `magyar_angol_konyvek_roviditesei.json`

**Mapping direction:** Hungarian abbreviation → English name
```json
{
  "1Móz": "Genesis",
  "2Móz": "Exodus",
  ...
  "Jel": "Revelation"
}
```

**Critical finding:** This file contains 66 books (Protestant canon). The Catholic deuterocanonical books are NOT included:
- Tobit (TOB)
- Judith (JDT)
- Wisdom of Solomon (WIS)
- Sirach/Ecclesiasticus (SIR)
- Baruch (BAR)
- 1 Maccabees (1MA)
- 2 Maccabees (2MA)

**Implication:** We need to handle two cases:
1. Books present in the mapping file (66 books) → use mapping to get English name → match against SZIT JSON keys
2. Deuterocanonical books (7 books) → need manual English name mapping

### English Book Names in SZIT JSON

Based on the mapping file, the SZIT JSON uses these English names:
- Standard names: "Genesis", "Exodus", "Leviticus", etc.
- Numbered books: "1Samuel", "2Samuel", "1Kings", "2Kings", "1Chronicles", "2Chronicles"
- New Testament: "1Corinthians", "2Corinthians", "1Thessalonians", etc.
- Special: "SongOfSongs" (not "Song of Solomon"), "Acts" (not "Acts of the Apostles")

### USX Code Mapping Chain

The mapping chain is:
```
SZIT JSON (English name) → Hungarian abbreviation → USX code
```

Example:
```
"Genesis" → "1Móz" → "GEN"
"1Samuel" → "1Sám" → "1SA"
"SongOfSongs" → "Én" → "SNG"
```

For deuterocanonical books (not in mapping file):
```
"Tobit" → manual → "TOB"
"Judith" → manual → "JDT"
"Wisdom" → manual → "WIS"
"Sirach" → manual → "SIR"
"Baruch" → manual → "BAR"
"1Maccabees" → manual → "1MA"
"2Maccabees" → manual → "2MA"
```

## Normalization Patterns

### Hungarian Text Characteristics
- **Diacritics:** á, é, í, ó, ö, ő, ú, ü, ű (NFC composed form standard)
- **Ligatures:** sz, zs, cs, dz, dzs, gy, ny, ty (not Unicode ligatures, just multi-character)
- **Abbreviations:** Book references use Hungarian abbreviations (e.g., "1Móz 1:1")
- **Whitespace:** May have inconsistent spacing around punctuation

### NFC Normalization
- Most Hungarian text is already NFC (Composed form)
- NFD (Decomposed form) uses combining characters (e.g., "a" + "́" for "á")
- NFC normalization ensures consistent representation
- Python `unicodedata.normalize('NFC', text)` handles this

### Verse Reference Format
- Hungarian format: "1Móz 1:1" (book abbrev + chapter:verse)
- USX format: "GEN 1:1" (USX code + chapter:verse)
- Need to standardize to one format for downstream use

## Validation Approach

### Verse Count Validation
- Compare verse count per chapter in SZIT JSON against `data/reference/versification.json`
- Report discrepancies with severity:
  - **ERROR:** Missing chapter (in schema but not in JSON)
  - **WARNING:** Verse count mismatch (different number of verses)
  - **INFO:** Extra chapter (in JSON but not in schema - may be apocryphal additions)

### Data Quality Checks
- Empty verse text (should be non-empty)
- Duplicate verse numbers (should be unique per chapter)
- Missing chapters (gaps in chapter sequence)
- Non-numeric chapter/verse keys (should be parseable as integers)

## Taskfile Integration

### Recommended Tasks
```yaml
text:fetch:
  desc: Download SZIT Bible JSON from GitHub
  cmds:
    - mkdir -p data/raw/text
    - curl -L -o data/raw/text/H_Kaldi_SZIT.json https://raw.githubusercontent.com/peterpolgar/Biblia-json-xml/main/bibles_json_dict/full_bibles/H_Kaldi_SZIT.json

text:normalize:
  desc: Normalize and validate Bible text
  cmds:
    - uv run bibliavox text normalize

text:validate:
  desc: Validate verse counts against versification schema
  cmds:
    - uv run bibliavox text validate
```

## Dependencies

### Python Standard Library
- `json` — JSON parsing
- `unicodedata` — NFC normalization
- `pathlib` — Path handling
- `re` — Regex for whitespace normalization

### No External Dependencies Required
- The text pipeline uses only standard library modules
- No network access after initial download (SZIT JSON is static)
- No ML/AI dependencies (unlike alignment phases)

## Risks and Mitigations

### Risk 1: Missing Deuterocanonical Books
**Impact:** 7 Catholic books not in mapping file
**Mitigation:** Hard-code English→USX mapping for deuterocanonical books

### Risk 2: Book Name Mismatches
**Impact:** English names in SZIT JSON may not match mapping file exactly
**Mitigation:** Build direct English→USX mapping, validate against SZIT JSON keys

### Risk 3: String Key Parsing
**Impact:** Chapter/verse numbers are strings, not integers
**Mitigation:** Explicit int() conversion with error handling

### Risk 4: Large File Size
**Impact:** SZIT JSON may be large (full Bible text)
**Mitigation:** Stream parsing if needed, but modern machines handle 10-50MB JSON easily

## Implementation Recommendations

1. **Book mapping approach:** Build a direct English→USX mapping dictionary (skip Hungarian abbreviation intermediary)
2. **Normalization pipeline:** Two-stage approach as decided in CONTEXT.md
3. **Data storage:** Store raw JSON as-is, processed text as structured JSON per book
4. **Validation output:** JSON discrepancy report with severity levels
5. **CLI structure:** Follow Pattern 4 (Typer Sub-Command Groups) from reference.py

---

*Research completed: 2026-05-29*
*Ready for planning: yes*
