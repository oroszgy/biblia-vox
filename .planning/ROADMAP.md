# Roadmap: BibliaVox

## Overview

Build a calibration-first pipeline that maps every verse of the Szent István Társulat Bible to precise timestamps in per-chapter audio recordings. The journey goes from foundational reference data through independent text and audio pipelines, into the critical alignment engine (the core product), and finishes with export and operational hardening — all validated on a gold subset of chapters before scaling.

Each phase delivers working Typer commands and Taskfile targets. Docker infrastructure is built incrementally when alignment phases need it.

## Phases

- [x] **Phase 1: Foundation & Versification Schema** - Canonical reference data, project structure, CLI scaffolding, and configuration for the Catholic Bible domain
- [x] **Phase 2: Text Acquisition & Validation** - Bible text fetched from SZIT JSON source, normalized, and validated against versification schema
- [x] **Phase 2.5: Data Quality & Correction** - JSONL conversion, verse splitting, and schema fixes for full validation (66/66 books)
- [x] **Phase 2.6: Alternate Text Source & Cross-Source Coverage Validation** - MEK text ingestion plus cross-source comparison to ensure complete book/chapter/verse coverage
- [x] **Phase 3: Audio Pipeline** - Chapter audio downloaded, decoded to WAV, and indexed for alignment
- [ ] **Phase 4: Transcription-Based Alignment** - Whisper transcription + fuzzy matching locates verses in audio (includes Docker setup for GPU models)
- [ ] **Phase 5: Forced Alignment & Alternatives** - MMS forced alignment tier plus VibeVoice and paid API exploration
- [ ] **Phase 6: Calibration & Alignment Comparison** - Gold-standard set built, approaches compared with quality metrics
- [ ] **Phase 7: Export & Pipeline Integration** - JSONL output with full metadata, end-to-end pipeline on gold subset
- [ ] **Phase 8: Operations & Pipeline Hardening** - Backup, status reporting, and checkpoint/resume for reliable operation

## Phase Details

### Phase 1: Foundation & Versification Schema
**Goal**: Project has canonical reference data, project structure, and initial CLI scaffolding for the 73-book Catholic Bible domain
**Depends on**: Nothing (first phase)
**Requirements**: TEXT-04, TEXT-06, INF-02
**Success Criteria** (what must be TRUE):
  1. User can import a versification module that returns all 73 Catholic books (including 7 deuterocanonical) with Hungarian names, abbreviations, and USX codes
  2. User can look up any book by Hungarian abbreviation and receive the canonical USX code (e.g., "Ter" → "GEN")
  3. User can load project configuration from environment/dotenv with sensible defaults for all paths, model settings, and API keys
  4. User can run `bibliavox --help` and see the CLI with initial sub-command structure, and `task --list` shows available targets
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Reference data & project structure (73-book schema, config, generation script)
- [x] 01-02-PLAN.md — CLI scaffolding & Taskfile (reference subcommands, dev tasks)

### Phase 2: Text Acquisition & Validation
**Goal**: Verified Bible text is available from a structured JSON source, normalized, and validated against versification schema
**Depends on**: Phase 1
**Requirements**: TEXT-01, TEXT-05
**Success Criteria** (what must be TRUE):
  1. User can run `bibliavox text fetch --book GEN --chapter 1` and see structured verse output from the SZIT JSON source
  2. User can run `bibliavox text normalize` on any Hungarian Bible verse text and get consistent diacritics (NFC), standardized whitespace, and normalized line endings
  3. User can run `task text:validate --book GEN --chapter 1` and receive a JSON discrepancy report showing location and severity of verse count mismatches against the versification schema
  4. User can run `bibliavox text info --book GEN` and see book metadata including chapter/verse counts
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Text source acquisition & book mapping (SZIT JSON download, English→USX mapping for 73 books)
- [x] 02-02-PLAN.md — Normalization pipeline & validation (NFC normalization, verse count validation, JSON reports)

### Phase 2.5: Data Quality & Correction
**Goal**: Fix Bible text data quality issues: convert to JSONL format, split embedded verses, and correct versification schema errors — so that `bibliavox text validate --all` passes for all 66 SZIT books
**Depends on**: Phase 2
**Requirements**: TEXT-01, TEXT-05
**Success Criteria** (what must be TRUE):
  1. User can run `task text:convert-jsonl` and see szit.jsonl created in data/processed/text/ with one JSON line per verse (USX codes, NFC text)
  2. User can run `task text:fix-verses` and see szit-fixed.jsonl created with embedded verse markers handled (63 Psalms cleanup, 4 splits)
  3. User can run `task text:validate --all` and see validation pass for all 66 SZIT books (0 discrepancies)
  4. versification.json has corrected counts: DAN 3 = 30 verses, MAL = 4 chapters, off-by-one books fixed
**Plans**: 3 plans

Plans:
- [x] 02.5-01-PLAN.md — JSONL Conversion (SZIT JSON → JSONL with USX codes, NFC normalization)
- [x] 02.5-02-PLAN.md — Verse Splitting (detect embedded verse markers, split or cleanup, validate 66/66)
- [x] 02.5-03-PLAN.md — Schema Fixes (correct versification.json for DAN, MAL, off-by-one books)

### Phase 2.6: Add alternate Bible text source (mek.oszk.hu) ingestion and completeness cross-source comparison across all books and verses
**Goal**: Verify and ingest alternate Bible text from mek.oszk.hu into a flat, normalized JSONL corpus for cross-source validation against SZIT text.
**Depends on**: Phase 2.5
**Requirements**: TEXT-02, TEXT-03
**Success Criteria** (what must be TRUE):
  1. User can run `go-task text:ingest-mek` and see MEK text downloaded, parsed with BeautifulSoup, and written to `data/processed/text/mek.jsonl`
  2. Raw chapter HTML files are cached in `data/raw/text/mek/` with format `{BOOK}_{CHAPTER}.html` for offline reproducibility
  3. User can run `go-task text:cross-validate` and see a Rich summary table highlighting all missing books, chapters, verses, and textual differences between SZIT and MEK
  4. All detected discrepancies are logged to `data/processed/text/text-discrepancies.jsonl` with correct severity level mapping
**Plans**: 2 plans

Plans:
- [x] 02.6-01-PLAN.md — MEK Text Ingestion & Parsing (BeautifulSoup parser, chapter caching, processed JSONL output)
- [x] 02.6-02-PLAN.md — Cross-Source Completeness & Validation CLI (cross-validator module, Rich summary CLI, JSONL diff output)

### Phase 3: Audio Pipeline
**Goal**: Chapter audio is downloaded, decoded to WAV 16kHz mono (eliminating VBR timestamp inaccuracy), and indexed for precise timestamp access
**Depends on**: Phase 1
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, AUD-05
**Success Criteria** (what must be TRUE):
  1. User can run `task audio:download BOOK=GEN CHAPTER=1` and see the MP3 downloaded with automatic retry on failure
  2. User can run `task audio:download-all WORKERS=4` and see multiple chapters downloading in parallel with configurable concurrency and progress indicators
  3. User can run `task audio:convert BOOK=GEN CHAPTER=1` and see the MP3 converted to WAV 16kHz mono with correct format verified
  4. User can run `bibliavox audio info --book GEN --chapter 1` and see duration, bitrate, sample rate metadata
  5. User can seek to a specific timestamp in the decoded WAV file and get accurate audio data (no VBR drift)
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Playlist discovery + resilient MP3 download (single + batch, retry/resume, mismatch diagnostics)
- [x] 03-02-PLAN.md — MP3→WAV conversion + ffprobe metadata CLI (strict 16k mono PCM invariants)
- [x] 03-03-PLAN.md — Seek index + prepare/seek workflows (sample-accurate WAV timestamp access)
- [x] 03-04-PLAN.md — Gap closure: executable Taskfile command contract + batch progress indicators

### Phase 4: Transcription-Based Alignment
**Goal**: Verses can be located in audio via faster-whisper transcription with Hungarian LoRA adapter, followed by fuzzy text matching against known verse text. Docker infrastructure for GPU models is set up as part of this phase.
**Depends on**: Phase 2, Phase 3
**Requirements**: ALN-01, ALN-02, ALN-08, INF-01, INF-03, INF-04, INF-05
**Success Criteria** (what must be TRUE):
  1. User can run `docker compose build whisper` and verify GPU access inside the container with the NVIDIA 3090 detected
  2. User can run `task align:transcribe --book GEN --chapter 1` and see timestamped word/segment output from faster-whisper with Hungarian LoRA
  3. User can run `task align:match --book GEN --chapter 1` and see per-verse match scores from RapidFuzz sliding-window matching against known verse text
  4. User can verify that silent segments produce no phantom verses (VAD-based silence detection working)
  5. User can inspect per-verse alignment results showing start_sec and end_sec timestamps for a test chapter
**Plans**: TBD

### Phase 5: Forced Alignment & Alternatives
**Goal**: Secondary alignment tier (MMS forced alignment) and exploratory approaches (VibeVoice, paid APIs) are available for comparison, with CTC drift compensation for long chapters
**Depends on**: Phase 4
**Requirements**: ALN-03, ALN-04, ALN-05, ALN-09
**Success Criteria** (what must be TRUE):
  1. User can run `task align:forced --book GEN --chapter 1` and get per-verse timestamps from torchaudio MMS_FA as a secondary precision tier
  2. User can see a documented feasibility assessment of VibeVoice as an alternative alignment approach (working prototype or reasoned rejection)
  3. User can see a cost/quality estimate for at least one paid API-based alignment service
  4. User can run alignment on a long chapter (30+ minutes) with CTC drift compensation (chunk-and-align with VAD anchoring) and verify timestamps remain accurate at chapter end
**Plans**: TBD

### Phase 6: Calibration & Alignment Comparison
**Goal**: Alignment approaches are compared on a gold-standard subset with documented quality metrics (WER, timestamp accuracy), and per-verse confidence scores are calibrated
**Depends on**: Phase 4, Phase 5
**Requirements**: ALN-06, ALN-07, ALN-10
**Success Criteria** (what must be TRUE):
  1. User can inspect a gold-standard calibration set of 50-100 manually aligned verses spanning 3-5 diverse chapters (narrative, poetry, proper-noun-heavy)
  2. User can run `task align:compare --gold` and see WER and timestamp accuracy metrics for each approach (transcribe-then-match vs forced alignment vs alternatives)
  3. User can see per-verse confidence scores that correlate with actual alignment accuracy on the gold set (higher scores = more accurate boundaries)
  4. User can read a comparison report documenting which approach works best for which chapter types and recommending a default strategy
**Plans**: TBD

### Phase 7: Export & Pipeline Integration
**Goal**: Alignment results are exported as JSONL with full metadata, and the full pipeline runs end-to-end on configurable gold subset chapters
**Depends on**: Phase 6
**Requirements**: EXP-01, EXP-02, EXP-03, EXP-04, EXP-05
**Success Criteria** (what must be TRUE):
  1. User can run `task export:jsonl --gold` and see JSONL output where every line contains: verse_ref, audio_file, start_sec, end_sec, source, translation, confidence
  2. User can run `task pipeline:run --gold` and see the full pipeline (text fetch → audio prep → alignment → export) execute on gold subset chapters in a single command
  3. User can verify that every verse in the gold subset chapters has a corresponding JSONL entry with non-null timestamps
  4. User sees Rich progress bars with stage indicators and ETA during the full pipeline run
  5. User can re-run the pipeline and see idempotent behavior (already-completed chapters are skipped unless --force is passed)
**Plans**: TBD

### Phase 8: Operations & Pipeline Hardening
**Goal**: Pipeline has rsync backup, status reporting, and checkpoint/resume for reliable unattended operation
**Depends on**: Phase 7
**Requirements**: OPS-01, OPS-02, OPS-03
**Success Criteria** (what must be TRUE):
  1. User can run `task backup:rsync` and see the data directory synced to the configured remote SFTP host
  2. User can run `bibliavox status` and see a pipeline status report showing which chapters are processed, which failed, and an alignment quality summary
  3. User can interrupt a pipeline run mid-chapter and resume from the last successful chapter on next run (no re-processing completed work)
**Plans**: TBD

## Progress

**Execution Order:**
Phase 1 first. Then Phases 2 and 3 can execute in parallel. Phase 2.5 fixes data quality after Phase 2. Phase 2.6 adds alternate text ingestion and cross-source completeness validation after Phase 2.5. Phase 4 requires text validation phases and Phase 3. Then sequential: 4 → 5 → 6 → 7 → 8.

```
Phase 1 (Foundation)
  ├── Phase 2 (Text)  ─── Phase 2.5 (Data Quality) ─── Phase 2.6 (Alt Text + Coverage) ─┐
  └── Phase 3 (Audio) ──────────────────────────────────────────────────────────────────────┼── Phase 4 (Transcription Alignment + Docker)
                                                      │         │
                                                      │    Phase 5 (Forced Alignment & Alternatives)
                                                      │         │
                                                      │    Phase 6 (Calibration & Comparison)
                                                      │         │
                                                      │    Phase 7 (Export & Pipeline Integration)
                                                      │         │
                                                      └── Phase 8 (Operations & Hardening)
```

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Versification Schema | 2/2 | Complete | 2026-05-29 |
| 2. Text Acquisition & Validation | 2/2 | Complete | 2026-05-29 |
| 2.5. Data Quality & Correction | 3/3 | Complete | 2026-05-29 |
| 2.6. Alternate Text Source & Cross-Source Coverage Validation | 2/2 | Planned | - |
| 3. Audio Pipeline | 4/4 | Complete | 2026-05-30 |
| 4. Transcription-Based Alignment | 0/? | Not started | - |
| 5. Forced Alignment & Alternatives | 0/? | Not started | - |
| 6. Calibration & Alignment Comparison | 0/? | Not started | - |
| 7. Export & Pipeline Integration | 0/? | Not started | - |
| 8. Operations & Pipeline Hardening | 0/? | Not started | - |
