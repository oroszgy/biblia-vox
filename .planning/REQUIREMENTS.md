# Requirements: BibliaVox

**Defined:** 2026-05-28
**Core Value:** Every verse of the Szent István Társulat Bible can be located in its audio recording — with precise timestamps and confidence metadata.

## v1 Requirements

v1 is a **calibration release**: build the full pipeline, validate it on a gold subset of chapters, explore alignment approaches, and prove the architecture works before scaling to the full Bible.

### Text Pipeline

- [ ] **TEXT-01**: Fetch verse text from szentiras.eu API (SZIT translation) with API key authentication
- [ ] **TEXT-02**: Parse mek.oszk.hu HTML pages as fallback/validation source
- [ ] **TEXT-03**: Cross-validate API vs HTML sources, flag discrepancies with location and severity
- [x] **TEXT-04**: Define 73-book Catholic versification schema (including 7 deuterocanonical books)
- [ ] **TEXT-05**: Normalize Hungarian text (diacritics, abbreviations, verse reference formats)
- [x] **TEXT-06**: Map Hungarian book abbreviations to USX codes (GEN, EXO, MAT, etc.)

### Audio Pipeline

- [ ] **AUD-01**: Download per-chapter MP3 files from mek.oszk.hu with retry and resume
- [ ] **AUD-02**: Parallel download of multiple chapters with configurable concurrency
- [ ] **AUD-03**: Decode MP3 to WAV 16kHz mono (critical for VBR timestamp accuracy)
- [ ] **AUD-04**: Extract audio metadata (bitrate, sample rate, duration) per file
- [ ] **AUD-05**: Build seek index for accurate timestamp access in WAV files

### Alignment Engine (Calibration Mode)

- [ ] **ALN-01**: Implement faster-whisper transcription with Hungarian LoRA adapter
- [ ] **ALN-02**: Implement RapidFuzz sliding-window matching against known verse text
- [ ] **ALN-03**: Implement torchaudio MMS_FA forced alignment as secondary precision tier
- [ ] **ALN-04**: Explore VibeVoice model as alternative alignment approach
- [ ] **ALN-05**: Explore paid API-based alignment services (cost/quality tradeoff)
- [ ] **ALN-06**: Create gold-standard calibration set (50-100 manually aligned verses across 3-5 chapters)
- [ ] **ALN-07**: Compute per-verse confidence scores for boundary detection
- [ ] **ALN-08**: Handle narrator silence/pauses (detect and skip hallucination zones)
- [ ] **ALN-09**: Compensate CTC drift on long chapters (chunk-and-align with VAD anchoring)
- [ ] **ALN-10**: Compare alignment approaches on gold subset, document quality metrics (WER, timestamp accuracy)

### Export & CLI

- [ ] **EXP-01**: JSONL output format: `{verse_ref, audio_file, start_sec, end_sec, source, translation, confidence}`
- [ ] **EXP-02**: Typer sub-commands: `text`, `audio`, `align`, `export`, `backup`
- [ ] **EXP-03**: Taskfile targets for each pipeline stage (download-text, download-audio, parse, align, export, backup)
- [ ] **EXP-04**: Rich progress display with stage indicators and ETA
- [ ] **EXP-05**: Pipeline runs end-to-end on gold subset chapters only (configurable chapter list)

### Infrastructure

- [ ] **INF-01**: Docker images for model-heavy stages (Whisper, MMS, VibeVoice) to isolate CUDA/PyTorch dependencies
- [x] **INF-02**: Native Python for lightweight stages (text parsing, audio download, export)
- [ ] **INF-03**: docker-compose.yml for orchestrating multi-stage pipeline
- [ ] **INF-04**: Shared data volume between containers and host for intermediate files
- [ ] **INF-05**: GPU passthrough configuration for Docker containers (NVIDIA Container Toolkit)

### Operations

- [ ] **OPS-01**: Rsync backup of data directory to remote SFTP host
- [ ] **OPS-02**: Pipeline status reporting (which chapters processed, alignment quality summary)
- [ ] **OPS-03**: Checkpoint and resume (restart from last successful chapter on failure)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scale to Full Bible

- **SCALE-01**: Process all 73 books (1189+ chapters) with batch optimization
- **SCALE-02**: Multi-variant support (different narrators, translations as separate variants)
- **SCALE-03**: Incremental processing (skip already-aligned chapters)

### Additional Output Formats

- **FMT-01**: SRT subtitle format output
- **FMT-02**: VTT subtitle format output
- **FMT-03**: Audacity label track format

### Additional Audio Sources

- **SRC-01**: YouTube audio extraction (Szent Jeromos playlists)
- **SRC-02**: androkat.hu daily gospel audio
- **SRC-03**: katolikusradio.hu liturgical readings

### Quality & Monitoring

- **QUAL-01**: Automated quality gates (reject alignments below confidence threshold)
- **QUAL-02**: Drift detection and correction across full Bible
- **QUAL-03**: Alignment quality dashboard

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Cross-translation alignment (Szent Jeromos vs Szent István) | Adds complexity; defer until v1 alignment is proven |
| TTS audio generation | Only aligning existing audio recordings |
| Web UI or API server | CLI-only tool |
| Real-time streaming or playback | Just mappings, not a player |
| Montreal Forced Aligner | Requires conda (incompatible with uv), Kaldi dependency chain |
| WhisperX | Critical word-timestamp bug history, adds unnecessary complexity |
| Full Bible processing in v1 | Calibration-first approach; scale after proving architecture |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEXT-01 | Phase 2 | Pending |
| TEXT-02 | Phase 2 | Pending |
| TEXT-03 | Phase 2 | Pending |
| TEXT-04 | Phase 1 | Complete |
| TEXT-05 | Phase 2 | Pending |
| TEXT-06 | Phase 1 | Complete |
| AUD-01 | Phase 3 | Pending |
| AUD-02 | Phase 3 | Pending |
| AUD-03 | Phase 3 | Pending |
| AUD-04 | Phase 3 | Pending |
| AUD-05 | Phase 3 | Pending |
| ALN-01 | Phase 4 | Pending |
| ALN-02 | Phase 4 | Pending |
| ALN-03 | Phase 5 | Pending |
| ALN-04 | Phase 5 | Pending |
| ALN-05 | Phase 5 | Pending |
| ALN-06 | Phase 6 | Pending |
| ALN-07 | Phase 6 | Pending |
| ALN-08 | Phase 4 | Pending |
| ALN-09 | Phase 5 | Pending |
| ALN-10 | Phase 6 | Pending |
| EXP-01 | Phase 7 | Pending |
| EXP-02 | Phase 7 | Pending |
| EXP-03 | Phase 7 | Pending |
| EXP-04 | Phase 7 | Pending |
| EXP-05 | Phase 7 | Pending |
| INF-01 | Phase 4 | Pending |
| INF-02 | Phase 1 | Complete |
| INF-03 | Phase 4 | Pending |
| INF-04 | Phase 4 | Pending |
| INF-05 | Phase 4 | Pending |
| OPS-01 | Phase 8 | Pending |
| OPS-02 | Phase 8 | Pending |
| OPS-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 after initial definition*
