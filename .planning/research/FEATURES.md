# Feature Landscape

**Domain:** Bible verse-to-audio alignment CLI tool
**Researched:** 2026-05-28
**Context:** Hungarian Catholic Bible (Szent Istvan Tarsulat) verse-to-audio mapping

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Bible text parsing (book/chapter/verse)** | Every Bible tool structures text this way. The core data model. | Low | Multiple format support (USFM, USX, OSIS, JSON API) is standard. `usfm-grammar`, `usfm3`, `BibleOrgSys` are mature Python options. szentiras.eu API provides structured JSON directly. |
| **Audio file download with retry/resume** | Audio sources are remote; downloads fail. Users expect resilience. | Low | `httpx`/`requests` with retry, exponential backoff, resume via `Range` headers. Skip already-downloaded files (idempotent). Progress bar via `rich` or `tqdm`. |
| **Forced alignment (text-to-audio sync)** | This IS the product. Every tool in this space does it. | High | Two main approaches: (1) TTS+DTW (aeneas) — language-agnostic but no confidence scores; (2) ASR-based CTC (MMS/wav2vec2 via TorchAudio) — produces per-token confidence, better for Hungarian. |
| **Verse-level timestamp output** | The entire value proposition. Users need start/end times per verse. | Low | Output: `verse_ref`, `audio_file`, `start_sec`, `end_sec`. JSONL is the right format for downstream consumption. |
| **Multiple output formats** | Different consumers need different formats. | Low | JSONL (primary), SRT/VTT (subtitles), CSV (spreadsheet), JSON (web). aeneas supports 12+ formats; follow that pattern. |
| **Progress tracking & status** | Alignment is slow (minutes per chapter). Users need feedback. | Low | Per-chapter progress, ETA, current book/chapter display. `rich` progress bars are standard for Python CLIs. |
| **Idempotent processing** | Re-running should skip completed work, not redo everything. | Low | Check output files exist before processing. `--force` flag to override. Standard CLI pattern. |
| **Batch processing** | 73 books, ~1200 chapters. Must handle bulk. | Medium | Process entire books or the full Bible in one command. Parallel chapter processing where possible (GPU is the bottleneck, so sequential alignment with parallel downloads). |
| **Error handling & reporting** | Audio may be corrupt, text may be missing, alignment may fail. | Medium | Structured error log, per-chapter success/failure summary, actionable error messages. Exit codes for CI use. |
| **Granular task workflow** | Users want to run individual steps (download only, align only, export only). | Low | Taskfile with separate tasks: `download-text`, `download-audio`, `parse`, `align`, `export`, `backup`. Matches project requirements. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Confidence scores per verse** | Know which alignments are trustworthy vs need manual review. Most tools (aeneas) don't provide this. | Medium | CTC-based forced alignment (TorchAudio MMS_FA) produces per-token probabilities that aggregate to word/verse confidence. FCBH uses this for audio proofing. Critical for quality control. |
| **Cross-validation (multi-source text)** | API text vs scraped HTML text — catch errors neither source alone would reveal. | Medium | szentiras.eu API + mek.oszk.hu HTML parsing. Diff the two sources. Unique approach; most tools trust a single source. |
| **Alignment quality validation report** | HTML report showing low-confidence verses with audio playback for manual review. | Medium | FCBH's approach: generate interactive HTML where reviewers play audio for each flagged verse. Prioritize by confidence score (lowest first). |
| **Multi-variant support** | Multiple narrators and translations as separate alignment variants in the same dataset. | Medium | Bible Analyzer indexes 8 different audio recordings for KJB. Schema: `variant_id` in JSONL output. Each (translation, narrator) pair is a variant. |
| **Hungarian-optimized alignment** | Hungarian is agglutinative with long words. Generic models underperform. | High | MMS supports Hungarian (1100+ languages). Fine-tuned Whisper Hungarian LoRA exists (~1.6GB, fixes hallucinations). wav2vec2-large-xlsr-53-hungarian achieves ~17% WER on Common Voice. Use Hungarian-specific models. |
| **rsync-based backup integration** | Data is valuable and not in git. Backup as a first-class workflow step. | Low | Most alignment tools don't include backup. rsync to SFTP host as a Taskfile task. Incremental, resumable. |
| **Fuzzy text matching for alignment** | Narrator may not read text verbatim (omissions, paraphrases, liturgical variants). | High | CTC forced alignment with `<star>` token handles missing transcript tokens. WhisperX uses wav2vec2 phoneme alignment for robustness. diff-match-patch (Myers algorithm) for post-alignment text comparison. |
| **Verse reference standardization** | Map between Hungarian abbreviations, USX codes (JHN_13_34), and numeric IDs (101=Teremtes). | Low | szentiras.eu GitHub repo provides abbreviation CSV, USX codes, and `tdverse` schema. Build a canonical reference mapper. |
| **GPU-accelerated local processing** | Nvidia 3090 available. Process entire Bible locally without cloud costs. | Low | TorchAudio forced alignment runs on CUDA. Whisper large-v3-turbo Hungarian LoRA fits in ~1.6GB VRAM. Batch processing with VAD segmentation for throughput. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time streaming/playback** | Massive complexity (WebSocket, buffering, sync). Not needed for mapping generation. | Output static JSONL. Downstream apps handle playback. |
| **TTS audio generation** | Out of scope. Only aligning existing recordings. | If audio is missing for a verse, flag it in the report. Don't generate it. |
| **Web UI / API server** | CLI-only by design. Web UI is a separate project. | JSONL output is the API. Consumers build their own UIs. |
| **Cross-translation alignment** | Aligning Szent Istvan text to Szent Jeromos audio requires handling translation differences. Premature. | Ship v1 with same-translation alignment only. Add cross-translation when v1 is solid. |
| **Speaker diarization** | Single narrator per audio file. No "who said what" problem. | Skip pyannote. Not needed for Bible narration. |
| **YouTube audio extraction** | Legal gray area, fragile (YouTube changes break scrapers). Deferred. | Use direct MP3 sources (mek.oszk.hu). Add YouTube in v2+ with yt-dlp if needed. |
| **Live sermon verse detection** | Completely different problem (real-time ASR + verse lookup). Rhema/Verse-Catch solve this. | Not this tool's domain. |
| **Bible text editing/correction** | Text sources are authoritative. Don't let users "fix" verses. | Flag discrepancies in validation report. Fix at source, not in this tool. |
| **Audio format conversion** | FFmpeg wrapper territory. Not the tool's job. | Accept MP3 input (matches source). Document required format. If conversion needed, user runs FFmpeg separately. |
| **Cloud API dependency for alignment** | GPU available locally. Cloud adds cost, latency, privacy concerns. | Local processing with TorchAudio/Whisper. Cloud Whisper only as optional fallback if local quality is insufficient. |

## Feature Dependencies

```
Bible text parsing → Alignment (need structured text to align)
Audio download → Alignment (need audio files to align)
Alignment → Export (need timestamps to export)
Alignment → Validation report (need confidence scores to flag issues)
Cross-validation → Text parsing (need both API and HTML parsers)
Verse reference standardization → All features (canonical refs used everywhere)
Multi-variant support → Alignment + Export (schema must support variants from start)
GPU acceleration → Alignment (local processing requires CUDA setup)
Backup → Export (back up output data, not raw downloads)
```

**Critical path:** Text parsing + Audio download → Alignment → Export → Validation

**Can parallelize:**
- Text parsing and audio download are independent
- Export and backup can run after alignment completes
- Validation report generation is independent of export format

## MVP Recommendation

Prioritize for v1 (Szent Istvan Tarsulat only, single narrator):

1. **Bible text parsing** (szentiras.eu API) — foundation for everything
2. **Audio download** (mek.oszk.hu MP3s) — with retry, resume, skip-existing
3. **Forced alignment** (TorchAudio MMS_FA or Whisper + wav2vec2) — verse-level timestamps with confidence
4. **JSONL export** — primary output format with full metadata
5. **Taskfile workflow** — granular tasks for each step
6. **Progress tracking** — per-chapter status during alignment
7. **Idempotent operations** — skip completed chapters

Defer to v2:
- **Cross-validation** (HTML parser): adds resilience but API alone works for v1
- **Multi-variant support**: schema should accommodate it, but only one variant in v1
- **Validation report**: useful but manual spot-checking works initially
- **SRT/VTT output**: only needed when a subtitle consumer appears
- **Backup integration**: important but not blocking for first alignment

Defer to v3+:
- **Cross-translation alignment**
- **YouTube audio sources**
- **Multi-narrator support**

## Hungarian Language Considerations

Hungarian speech recognition has specific challenges and available resources:

| Resource | Type | Hungarian WER | Notes |
|----------|------|---------------|-------|
| MMS (Meta) | Multilingual ASR + forced alignment | Not published for HU specifically, but trained on Bible audio | 1100+ languages. Trained partly on FCBH Bible recordings. Best bet for Bible-domain Hungarian. |
| Whisper large-v3-turbo Hungarian LoRA | Fine-tuned Whisper | Fixes hallucinations, special characters | ~1.6GB VRAM. CTranslate2 accelerated. Good for transcription step. |
| wav2vec2-large-xlsr-53-hungarian | Fine-tuned wav2vec2 | ~17% WER (Common Voice 17) | Best open wav2vec2 for Hungarian. Suitable for forced alignment phoneme model. |
| Whisper large-v2 HU (Trendency) | Fine-tuned Whisper | ~16% WER (FLEURS) | Full fine-tune, larger model. |
| aeneas + eSpeak HU | TTS+DTW | N/A (no WER metric) | Language-agnostic approach. No confidence scores. eSpeak Hungarian TTS available. |

**Recommendation:** Use MMS forced alignment via TorchAudio (`torchaudio.pipelines.MMS_FA`) as primary. It supports Hungarian, produces confidence scores, and was trained on Bible audio. Fall back to Whisper + wav2vec2 Hungarian if MMS quality is insufficient for the specific narrator's speech patterns.

## Sources

- **Timestamp Audio** (timestampaudio.com) — Bible verse timestamping service, 5.1M verses processed. JSON/SRT output. [MEDIUM confidence: commercial product, feature list verified]
- **Bible Analyzer** (bibleanalyzer.com) — Exact verse timing for 8 KJB audio sets. Multiple indexed recordings. [MEDIUM confidence: commercial product, feature list verified]
- **aeneas** (github.com/readbeyond/aeneas) — TTS+DTW forced alignment. 12+ output formats. No confidence scores (explicit design decision). 3K+ GitHub stars. [HIGH confidence: open source, well-documented]
- **TorchAudio MMS_FA** (pytorch.org/audio) — CTC forced alignment with MMS. Per-token confidence scores. Hungarian supported. [HIGH confidence: official PyTorch documentation]
- **FCBH dataset-io** (github.com/faithcomesbyhearing/fcbh-dataset-io) — Audio proofing via MMS + diff-match-patch. HTML validation reports. [MEDIUM confidence: open source, specialized tool]
- **WhisperX** (github.com/m-bain/whisperX) — Whisper + wav2vec2 forced alignment. Sub-100ms word timestamps. VAD segmentation. [HIGH confidence: widely used, well-documented]
- **ctc-forced-aligner** (github.com/MahmoudAshraf97/ctc-forced-aligner) — MMS/wav2vec2/HuBERT alignment. Sentence/word/char granularity. [MEDIUM confidence: open source, recent]
- **Whisper Hungarian LoRA** (github.com/Maxdorger/whisper-hungarian-lora) — CTranslate2 accelerated, fixes hallucinations. [LOW confidence: single-source, recent project]
- **wav2vec2-large-xlsr-53-hungarian** (huggingface.co/sarpba) — ~17% WER on Common Voice 17. [MEDIUM confidence: HuggingFace model card, benchmark results]
- **Scripture App Builder** (SIL) — aeneas integration for Bible audio apps. Verse and phrase-level timing. [HIGH confidence: SIL documentation]
- **MaSS corpus** (aclanthology.org) — Multilingual Bible speech corpus including Hungarian. Maus forced aligner pipeline. [HIGH confidence: peer-reviewed paper]
- **usfm3** (github.com/jcuenod/usfm3) — Rust-based USFM parser with Python bindings. Error-tolerant. [MEDIUM confidence: open source, recent]
- **usfm-grammar** (pypi.org) — Python USFM parser via tree-sitter. USX/USJ/dict output. [MEDIUM confidence: PyPI package]
