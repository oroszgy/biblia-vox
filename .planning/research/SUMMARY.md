# Project Research Summary

**Project:** cath-bible-voice
**Domain:** Bible verse-to-audio alignment CLI (Hungarian Catholic Bible)
**Researched:** 2026-05-28
**Confidence:** HIGH (stack, architecture), MEDIUM (alignment model selection, Hungarian ASR quality)

## Executive Summary

This project is a **linear data pipeline CLI tool** that maps every verse of the Hungarian Catholic Bible (Szent István Társulat translation) to precise timestamps in per-chapter MP3 audio recordings. The domain is well-understood: Bible audio alignment tools exist commercially (Timestamp Audio, Bible Analyzer) and in open source (aeneas, WhisperX, ctc-forced-aligner), but none are optimized for Hungarian or Catholic versification. The recommended approach is a **transcribe-then-match** strategy using faster-whisper with a Hungarian LoRA adapter for speech recognition, combined with fuzzy text matching via RapidFuzz to locate verses in the transcription. A secondary tier using torchaudio's MMS forced alignment is available for verses where fuzzy matching produces low confidence.

The stack is well-researched and GPU-feasible: the entire pipeline fits in ~8-10GB VRAM on the available RTX 3090. The architecture follows a **stage-based pipeline with per-chapter processing and checksum-based caching** — each stage (text fetch, audio prep, alignment, export) produces disk artifacts enabling incremental re-runs and debugging. The critical architectural decision is transcribe-then-match over forced-alignment-with-known-text, because it avoids needing a Hungarian pronunciation dictionary for Bible vocabulary and handles minor narrator deviations gracefully through fuzzy matching.

The **key risks** are: (1) VBR MP3 files from mek.oszk.hu will produce inaccurate seek positions for downstream consumers unless decoded to WAV before any timestamp work; (2) Whisper hallucination during silence segments can produce phantom verses; (3) CTC-based alignment drifts on long chapters (30+ minutes); (4) Catholic versification differs from Protestant norms in Psalms and deuterocanonical books. All four risks have known mitigations documented in the pitfalls research, but each requires deliberate implementation from the start — they cannot be bolted on later.

## Key Findings

### Recommended Stack

The stack builds on the existing project constraints (Python 3.13+, uv, typer, ruff, ty, Taskfile) and adds ML/audio libraries chosen for Hungarian language support and GPU efficiency.

**Core technologies:**
- **faster-whisper** (>=1.2.1): Speech-to-text — 4x faster than OpenAI Whisper at same accuracy, int8 quantization, native word timestamps via cross-attention + DTW, built-in Silero VAD
- **Maxdorger29/whisper-large-v3-turbo-hungarian-lora**: Hungarian Whisper model — LoRA fine-tuned for Hungarian, fixes hallucinations on Hungarian characters/names, ~1.6GB VRAM
- **torchaudio MMS_FA** (>=2.8): Forced alignment fallback — multilingual wav2vec2 covering 1130 languages including Hungarian, CUDA-accelerated `forced_align()` API
- **rapidfuzz** (>=3.14): Fuzzy string matching — C++ backed, 40% faster than alternatives, multi-core batch comparison
- **pydub + soundfile**: Audio I/O — pydub for high-level MP3 slicing, soundfile for low-level numpy array I/O at native sample rate
- **httpx** (>=0.28): HTTP client — async support for parallel API calls, modern API design

**Critical version requirements:**
- Python >=3.13 (project constraint)
- faster-whisper >=1.2.1 (word_timestamps support)
- torchaudio >=2.8 (MMS_FA bundle, maintenance mode but forced_align preserved)
- torch >=2.5 (required by faster-whisper, torchaudio)

### Expected Features

**Must have (table stakes):**
- Bible text parsing (book/chapter/verse) from szentiras.eu API — the foundational data model
- Audio file download with retry/resume from mek.oszk.hu — remote source resilience
- Forced alignment producing verse-level timestamps — this IS the product
- JSONL export with full metadata — primary output format
- Progress tracking per chapter — alignment takes minutes per chapter
- Idempotent processing — skip completed work on re-run
- Taskfile granular workflow — separate tasks for each pipeline stage

**Should have (competitive differentiators):**
- Confidence scores per verse — know which alignments need manual review
- Cross-validation (API vs HTML text sources) — catch errors neither source reveals alone
- Hungarian-optimized alignment models — generic models underperform on agglutinative Hungarian
- Fuzzy text matching for alignment — handles narrator omissions, paraphrases, liturgical variants
- Verse reference standardization — map Hungarian abbreviations, USX codes, and numeric IDs

**Defer (v2+):**
- Cross-validation HTML parser — API alone works for v1
- Multi-variant support — schema accommodates it, but only one variant in v1
- Validation HTML report — manual spot-checking works initially
- SRT/VTT subtitle output — only needed when a subtitle consumer appears
- Cross-translation alignment, YouTube sources, multi-narrator support

### Architecture Approach

The tool is a **linear data pipeline with stage-based caching**. Each stage produces intermediate artifacts on disk (raw text, parsed verses, prepared audio, per-chapter alignments, final JSONL), enabling incremental re-runs, debugging, and checkpoint recovery. The chapter is the fundamental processing unit — all stages operate on one chapter at a time, matching the audio source structure and limiting memory usage.

**Major components:**
1. **Text Module** (`text/`) — Fetch Bible text from API/HTML, parse, normalize Hungarian diacritics, cross-validate sources
2. **Audio Module** (`audio/`) — Download MP3s, convert to WAV 16kHz mono (required by ML models), extract metadata
3. **Alignment Module** (`align/`) — Load model, generate CTC emissions, run forced alignment, produce per-verse timestamps with confidence
4. **Export Module** (`export/`) — Flatten per-chapter alignments into single JSONL with metadata enrichment
5. **Cache Layer** (`cache/`) — Checksum-based invalidation for expensive intermediate artifacts (emissions, audio conversions)
6. **Reference Data** (`reference/`) — Book abbreviations, USX codes, verse schema from szentiras.eu GitHub repo

**Key patterns:** Protocol-based module interfaces (swap text sources, swap alignment models), Typer sub-command groups per module, Rich progress for long operations, model loaded once per batch run (not per chapter).

### Critical Pitfalls

1. **VBR MP3 Timestamp Inaccuracy** — mek.oszk.hu MP3s are likely Variable Bitrate. VBR seeking can be off by 3-10+ seconds. **Prevention:** Decode all MP3s to WAV 16kHz before any alignment work. Store timestamps relative to decoded audio. Re-encode to CBR or build a seek index if downstream consumers need the original MP3.

2. **Whisper Hallucination on Silence** — Whisper fabricates text during silent segments and narrator pauses, producing phantom verses with high confidence. **Prevention:** Use Silero VAD as pre-processing to segment speech/non-speech. Set `condition_on_previous_text=False`. Cross-validate transcriptions against known verse text — discard segments that don't fuzzy-match any expected verse.

3. **CTC Forced Alignment Drift** — CTC-based alignment accumulates timing error over long chapters (30+ min), with timestamps drifting 3-5 seconds by chapter end. **Prevention:** Chunk-and-align strategy with overlapping segments. Anchor to VAD-detected silence regions (often verse boundaries). Validate with spot checks at beginning, middle, and end of each chapter.

4. **Catholic Verse Numbering Mismatches** — Catholic versification differs from Protestant in Psalms (numbering shifts), deuterocanonical books (7 extra books), and verse splits/merges. **Prevention:** Use szentiras.eu API as single versification authority. Build a versification mapping table from the `tdverse` schema. Validate verse counts per chapter. Test with known problem books (Psalms, Daniel, Numbers 25-26).

5. **Hungarian ASR Accuracy Insufficient for Naive Transcription** — Even fine-tuned Hungarian Whisper has 7-25% WER. Agglutinative morphology means ASR errors produce valid but wrong Hungarian words. **Prevention:** Use forced alignment (align known text to audio) rather than transcription + matching. If using Whisper, use it only for validation against forced alignment results.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation & Reference Data
**Rationale:** Every other phase depends on configuration, paths, and the canonical book/verse schema. This must be rock-solid before any I/O begins. The Catholic versification mapping table (Pitfall 4) is a prerequisite for text validation.
**Delivers:** `config.py` (Pydantic Settings, paths, model config), `reference/` module (73-book schema, USX codes, Hungarian abbreviations from szentiras.eu `tdverse`), `cache/store.py` (disk-based checksum cache), project structure (src-layout)
**Addresses:** Verse reference standardization (feature), granular task workflow (Taskfile setup)
**Avoids:** Catholic verse numbering mismatches (Pitfall 4) — build the mapping table now, not after alignment is built

### Phase 2: Text Pipeline
**Rationale:** Text is the "known" side of the alignment equation. Must be acquired and validated before alignment can begin. Independent of audio — can be built and tested in isolation. The API client is the primary path; HTML parser is the fallback/cross-validator.
**Delivers:** `text/api_client.py` (szentiras.eu API), `text/html_parser.py` (mek.oszk.hu scraper), `text/normalizer.py` (Hungarian NFC normalization, punctuation stripping), `text/validator.py` (cross-source diff), `data/raw/text/` and `data/parsed/verses.json`
**Uses:** httpx, beautifulsoup4, lxml, rapidfuzz, unicodedata
**Implements:** Text Module with Protocol-based TextSource interface
**Avoids:** Text source fragility (Pitfall 8) — cache aggressively, validate completeness, checksum data

### Phase 3: Audio Pipeline
**Rationale:** Audio must be downloaded and converted to WAV before alignment. The VBR MP3 issue (Pitfall 1) makes the MP3→WAV conversion a critical preprocessing step, not an optional optimization. Independent of text pipeline — can be built in parallel with Phase 2.
**Delivers:** `audio/downloader.py` (MP3 download with retry/resume/skip-existing), `audio/preparer.py` (MP3→WAV 16kHz mono conversion via ffmpeg), metadata sidecars, `data/raw/audio/` and `data/prepared/audio/`
**Uses:** pydub, soundfile, ffmpeg (system dependency)
**Implements:** Audio Module, per-chapter file organization
**Avoids:** VBR MP3 timestamp inaccuracy (Pitfall 1) — decode to WAV before any timestamp work. MP3 encoder delay (Pitfall 7) — measure and document offset.

### Phase 4: Alignment Engine (Critical Path)
**Rationale:** This is the core value of the product and depends on both text (Phase 2) and audio (Phase 3) being ready. The alignment strategy (transcribe-then-match with fuzzy matching, plus forced alignment as secondary) is the central architectural decision. This phase needs prototyping on 3-5 sample chapters before full implementation.
**Delivers:** `align/model.py` (model loading, device management), `align/text_prep.py` (Hungarian text tokenization for alignment), `align/emissions.py` (CTC emission generation), `align/alignment.py` (Viterbi alignment, span extraction), `align/postprocess.py` (confidence scoring, segment merging), `data/aligned/{book}/{chapter}.json`
**Uses:** faster-whisper + Hungarian LoRA, torchaudio MMS_FA, sarpba/wav2vec2-large-xlsr-53-hungarian, rapidfuzz, torch/ctranslate2
**Implements:** Two-tier alignment strategy (fuzzy matching primary, forced alignment secondary), per-chapter processing with cached emissions
**Avoids:** Whisper hallucination (Pitfall 2) — VAD pre-filtering, cross-validate against known verses. CTC drift (Pitfall 3) — chunk-and-align with VAD anchoring. Hungarian ASR accuracy (Pitfall 5) — use forced alignment, not naive transcription.

### Phase 5: Export & CLI Assembly
**Rationale:** Wraps the pipeline into the user-facing interface. Depends on alignment output format being stable (Phase 4). This is where the Taskfile workflow and Typer commands come together.
**Delivers:** `export/jsonl.py` (JSONL writer with metadata enrichment), all `cli/*.py` command groups (text, audio, align, export, backup), `main.py` (Typer entry point), complete Taskfile with all targets
**Uses:** typer, rich (progress bars), json (stdlib)
**Implements:** Typer sub-command groups, Rich progress for long operations, idempotent processing with `--force` flag

### Phase 6: Validation & Operations
**Rationale:** Quality assurance and data protection. The confidence calibration (Pitfall 9) requires a gold-standard set that can only be built after alignment is working. Backup must be configured before any large processing runs.
**Delivers:** Gold-standard verse set (50-100 manually aligned verses), confidence calibration, validation report generator, rsync backup Taskfile task, end-to-end pipeline test on full Bible
**Addresses:** Confidence scores (differentiator), alignment quality validation report (differentiator), rsync backup integration

### Phase Ordering Rationale

- **Phases 2 and 3 are independent** — can be built in parallel or either first. Neither depends on the other.
- **Phase 4 is the critical path** — depends on both text and audio outputs. This is where the product's core value is delivered and where the most technical risk lives.
- **Phase 1 must come first** — the reference data (73-book Catholic schema, versification mapping) is a prerequisite for text validation in Phase 2 and alignment validation in Phase 4.
- **Phase 5 wraps everything** — the CLI and export layer is thin once the pipeline stages work correctly.
- **Phase 6 is last but not optional** — confidence calibration and backup are essential for production use, but require a working pipeline to build the gold-standard set.
- **This ordering avoids the "build alignment first, discover data problems later" trap** — text and audio pipelines are independently testable, producing verified artifacts before the expensive alignment step.

### Research Flags

Phases likely needing deeper research during planning (`/gsd-research-phase`):
- **Phase 4 (Alignment Engine):** The most technically complex phase. Needs prototyping of both alignment strategies (transcribe-then-match vs. CTC forced alignment) on sample chapters. The choice between faster-whisper word timestamps + fuzzy matching vs. torchaudio MMS_FA may need empirical testing. Hungarian-specific model performance on Bible narration audio is unverified.
- **Phase 2 (Text Pipeline):** The szentiras.eu API needs an API key (email maintainers) — availability and rate limits are unverified. The mek.oszk.hu HTML structure needs parser prototyping. Latin-2 encoding handling may be needed.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Well-documented patterns (Pydantic Settings, src-layout, disk cache). No unknowns.
- **Phase 3 (Audio Pipeline):** Standard download + ffmpeg conversion. Well-understood patterns.
- **Phase 5 (Export & CLI):** Typer sub-commands, JSONL writing, Rich progress — all standard Python CLI patterns.
- **Phase 6 (Operations):** rsync backup is a shell command. Confidence calibration is domain-specific but low-complexity.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core stack verified against official docs, benchmarks, and GitHub repos. faster-whisper, torchaudio MMS_FA, rapidfuzz all well-documented. Hungarian LoRA model is MEDIUM confidence (community project, single source). |
| Features | HIGH | Feature landscape derived from multiple commercial and open-source Bible alignment tools. Table stakes and differentiators well-established. MVP scope is clear. |
| Architecture | HIGH | Pipeline architecture follows established patterns from easyaligner, ctc-forced-aligner, and FCBH dataset-io. Component boundaries and data flow are well-defined. |
| Pitfalls | HIGH | All 5 critical pitfalls documented with academic/official sources (peer-reviewed CTC drift papers, official Whisper issues, ExoPlayer VBR seeking). Mitigations are proven. |

**Overall confidence:** HIGH

### Gaps to Address

- **szentiras.eu API availability:** API key requires emailing maintainers. If unavailable or rate-limited, the HTML parser becomes the primary source, not just a fallback. **Handle during Phase 2 planning:** contact maintainers early, have HTML parser ready as primary.

- **mek.oszk.hu audio completeness:** Unknown whether all 73 Catholic books (including 7 deuterocanonicals) have audio. **Handle during Phase 3 planning:** verify audio file listing before designing the pipeline. If books are missing, flag them as text-only in output.

- **Alignment model performance on Bible narration:** Hungarian Whisper LoRA and wav2vec2 models were benchmarked on Common Voice (conversational speech), not Bible narration (literary register, single speaker, long-form). **Handle during Phase 4:** prototype on 3-5 diverse chapters (narrative, poetry, proper-noun-heavy) before committing to a strategy.

- **Confidence score calibration:** No ground truth exists. The relationship between CTC posterior scores / fuzzy match ratios and actual alignment accuracy is unknown for this specific audio. **Handle during Phase 6:** create a 50-100 verse gold-standard set manually, use it to calibrate thresholds.

- **TorchAudio maintenance mode:** TorchAudio 2.8+ is in maintenance mode. The `forced_align()` API is preserved but no new features will be added. **Low risk:** the API is stable and sufficient for our needs. Monitor for deprecation warnings in future versions.

## Sources

### Primary (HIGH confidence)
- faster-whisper GitHub (22K stars, MIT, v1.2.1) — speech recognition engine, word_timestamps, batched inference
- torchaudio MMS_FA official PyTorch docs — forced alignment API, 1130 language support
- WhisperX PR #1367 — critical word-timestamp bug documentation (v3.3.3-v3.8.1)
- ctc-forced-aligner (MahmoudAshraf97) — CTC alignment pipeline with MMS support
- easyaligner (kb-labb) — modular 3-stage alignment with intermediate caching
- ExoPlayer MP3 seeking issue #6787 — VBR seeking inaccuracy documentation
- LFA/BRCTC peer-reviewed papers — CTC drift fundamental limitations
- OpenAI Whisper discussions #1606, PR #1838 — hallucination on silence behavior
- LAME encoder delay documentation — MP3 padding technical details
- szentiras.eu GitHub repo — book abbreviations, USX codes, tdverse schema

### Secondary (MEDIUM confidence)
- sarpba/wav2vec2-large-xlsr-53-hungarian HuggingFace model card — 17% WER on CV17
- Maxdorger29/whisper-large-v3-turbo-hungarian-lora — Hungarian LoRA, CTranslate2-native
- sarpba/whisper-hu-large-v3-turbo-finetuned — 7.5% WER community benchmarks
- FCBH dataset-io — audio proofing via MMS + diff-match-patch, HTML validation reports
- aeneas (3K+ stars) — TTS+DTW forced alignment, 12+ output formats
- RapidFuzz benchmarks — 40% faster than alternatives, C++ backend
- Catholic Bible versification resources — Psalm numbering, deuterocanonical books
- Hungarian ASR dataset papers (arxiv) — low-resource language challenges

### Tertiary (LOW confidence)
- Whisper Hungarian LoRA (Maxdorger/whisper-hungarian-lora) — single-source community project, needs validation
- Timestamp Audio / Bible Analyzer commercial products — feature lists verified but implementation details unknown
- mek.oszk.hu audio collection structure — not yet verified programmatically

---
*Research completed: 2026-05-28*
*Ready for roadmap: yes*
