# BibliaVox

## What This Is

A CLI workflow (Taskfile + Python/uv/typer) that maps Hungarian Catholic Bible verses (Szent István Társulat translation) to audio file timestamps. The output is a JSONL of verse-to-audio mappings with metadata. The system aligns existing audio recordings to known verse text, and is designed to extend to multiple narrators and translations over time.

## Core Value

Every verse of the Szent István Társulat Bible can be located in its audio recording — with precise timestamps and confidence metadata.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Fetch and parse Szent István Társulat Bible text (structured by book/chapter/verse)
- [ ] Download per-chapter MP3 audio files from mek.oszk.hu
- [ ] Align audio to verses within each chapter (produce verse-level timestamps)
- [ ] Export JSONL mappings: verse_ref, audio_file, start_sec, end_sec, source, translation, confidence
- [ ] Taskfile workflow with granular tasks (download-text, download-audio, parse, align, export, backup)
- [ ] Cross-validate text sources (API vs HTML scraping)
- [ ] Rsync-based backup of data to remote host

### Out of Scope

- Cross-translation alignment (Szent Jeromos vs Szent István) — defer until v1 is solid
- TTS audio generation — only aligning existing audio
- Web UI or API server — CLI only
- Real-time streaming or playback — just mappings
- YouTube audio extraction — defer to later phases

## Context

**Domain:** Hungarian Catholic Bible digital tools. The Szent István Társulat translation is the standard Catholic Hungarian Bible. Audio recordings exist as per-chapter MP3s on mek.oszk.hu.

**Text sources (v1):**
- **szentiras.eu API** (primary) — structured JSON per verse, SZIT translation available, needs API key (email maintainers). Endpoints: `/api/ref/{ref}/SZIT`, `/api/forditasok/{ref}`, book listing. Uses USX codes (JHN_13_34 format) and Hungarian abbreviations.
- **mek.oszk.hu HTML** (fallback/validation) — the original source at https://mek.oszk.hu/00100/00176/html/, needs custom HTML parser.

**Audio source (v1):**
- **mek.oszk.hu MP3s** — per-chapter files at https://mek.oszk.hu/08800/08820/mp3/index.html. This is the Szent István Társulat audio (same translation as text target).

**Alignment approach:** Undecided — candidates are Whisper transcription + fuzzy text matching, or forced alignment models (MMS/wav2vec). The machine has an Nvidia 3090 for local processing. Willing to pay for cloud transcription if cost-effective.

**Reference data from szentiras.eu GitHub repo (AGPL):**
- Book abbreviations CSV: 73 books with Hungarian names, abbreviations, numeric IDs (101=Teremtés..227=Jelenések)
- USX codes: standard Bible book codes (GEN, EXO... MAT, MRK...)
- Verse schema: `tdverse` table with `trans`, `gepi` (machine code: `{bookNum}{chapter:3d}{verse:3d}00`), `usx_code`, `chapter`, `numv`, `verse` (text), `tip` (type)
- Actual Bible text NOT in the repo — loaded from external Excel files or production DB

**Future audio sources (v2+):**
- YouTube: Szent Jeromos New Testament playlist
- YouTube: Szent Jeromos full Bible
- YouTube: In-progress podcast with commentary
- androkat.hu: daily gospel audio
- katolikusradio.hu: liturgical readings

**Variants:** Multiple narrators AND multiple translations, each as a separate variant in the mapping.

## Constraints

- **Tech stack**: Python 3.13+, uv, typer, ruff, ty — already initialized in pyproject.toml
- **Workflow**: Taskfile (go-task) for orchestrating granular tasks
- **Data policy**: Data not versioned in git, backed up via rsync to remote SFTP host
- **Hardware**: Nvidia 3090 available for local audio processing
- **License**: szentiras.eu code is AGPL — text data usage terms TBD (contact maintainers for API key)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Start with Szent István Társulat only | Same translation for text and audio avoids cross-translation alignment complexity | — Pending |
| Use Biblia-json-xml as primary text source | szentiras.eu API requires email keys and is non-viable; Biblia-json-xml has clean offline SZIT database | — Success |
| Ingest MEK HTML as alternate/validation | Cross-validate corpora to discover book/chapter/verse and text discrepancies | — Success |
| Cache raw MEK HTML at chapter level | Avoids redundant network requests and ensures fully offline reproducible parses | — Success |
| Combine verse suffixes into integer indices | Suffixes like '12a' are space-joined under verse index '12' to align with canonical versification | — Success |
| Whitespace collapse & NFC normalization | NFC normalizes and collapses all whitespaces and newlines to eliminate formatting differences | — Success |
| Output detailed discrepancy Rich table cap | Caps stdout to 100 entries to prevent terminal flooding and potential DOS | — Success |
| Per-chapter MP3 granularity | Matches mek.oszk.hu source structure | — Pending |
| JSONL output with full metadata | Flexible for downstream consumers, includes confidence scores | — Pending |
| Taskfile for workflow | Granular tasks, reproducible, standard tooling | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-30 after Phase 2.6*
