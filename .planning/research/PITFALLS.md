# Domain Pitfalls

**Domain:** Bible audio alignment CLI (Hungarian Catholic Bible, per-chapter MP3 → verse-level timestamps)
**Researched:** 2026-05-28

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or fundamentally wrong output.

### Pitfall 1: MP3 VBR Timestamp Inaccuracy

**What goes wrong:** The mek.oszk.hu MP3 files are likely Variable Bitrate (VBR). VBR MP3s have no inherent timestamp-to-byte mapping. Seeking by average bitrate estimate can produce errors of 3–10+ seconds — especially in long chapter files (20–40 min). Any downstream consumer using your timestamps to seek into the MP3 will land at the wrong verse.

**Why it happens:** MP3 is a frame-based format with no absolute timestamps. VBR files encode different frames at different bitrates (e.g., 32 kbps for silence, 320 kbps for complex speech). The Xing/VBRI header provides only a coarse Table of Contents (100 entries for the entire file), meaning resolution degrades with file length. ExoPlayer's documentation explicitly states: "The Xing format is very poor for seeking accuracy, especially for long files."

**Consequences:** Verse timestamps appear correct during alignment (which works on decoded PCM), but every downstream player/app that seeks into the original MP3 will be off by seconds. Users hear the wrong verse. The error is non-linear — it varies by position in the file and is worst in the middle-to-end.

**Prevention:**
1. **Decode to WAV/FLAC before alignment.** Run `ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav` and align against the decoded PCM. Store timestamps relative to the decoded audio.
2. **Re-encode to CBR or a seekable format** (Opus/OGG) for distribution if downstream consumers need to seek. CBR MP3 seeking is accurate to within one frame (~26ms at 44.1kHz).
3. **Build a seek index** if you must keep VBR MP3s: scan the entire file once, build a frame-level byte-offset-to-timestamp map, and store it alongside your JSONL output.
4. **Document the audio format assumption** in your output metadata — downstream consumers need to know if timestamps are relative to decoded PCM or the original MP3.

**Detection:** Compare seek positions: seek to a timestamp using ffmpeg (`-ss`) vs. a media player. If they diverge by more than 100ms, the file has VBR seek issues. Run `ffprobe -show_format` and check for `bit_rate` vs. actual per-frame bitrates.

**Phase mapping:** Must be addressed in the audio download/preprocessing phase (before alignment). If missed, all alignment output is suspect for downstream use.

---

### Pitfall 2: Whisper Hallucination on Silence and Pauses

**What goes wrong:** Whisper generates plausible-sounding but completely fabricated text during silent segments, narrator pauses between chapters/verses, or low-energy audio. Common hallucinations include repeated phrases, "Thank you for watching", "Subtitles by...", or looping the last recognized sentence. This produces phantom verses with high confidence scores.

**Why it happens:** Whisper was trained on YouTube videos with subtitles. During silence, the decoder fills in text from its training distribution. The `no_speech_prob` heuristic is unreliable — it often fails to detect extended silence. Fine-tuned Hungarian models (e.g., `sarpba/whisper-large-v2-CV18-hu-cleaned`) inherit this behavior. The problem is worse with `condition_on_previous_text=True` (default), which causes looping.

**Consequences:** Your alignment pipeline assigns hallucinated text to audio segments, producing verse mappings for text that was never spoken. This corrupts the JSONL output silently — the structure looks valid, but the content is wrong. Particularly dangerous for Psalms (short verses, many pauses) and narrative books with dramatic pauses.

**Prevention:**
1. **Use VAD (Voice Activity Detection) as a pre-processing step.** Silero VAD (`snakers4/silero-vad`) segments audio into speech/non-speech regions. Only run Whisper on VAD-detected speech segments.
2. **Set `hallucination_silence_threshold`** (available in patched Whisper and faster-whisper) to skip silence before inference.
3. **Use `condition_on_previous_text=False`** to prevent looping, at the cost of some context quality.
4. **Post-process:** Flag any segment where `no_speech_prob > 0.5` or `compression_ratio > 2.4` as suspect. Cross-validate against known verse text — if the transcription doesn't fuzzy-match any expected verse in the chapter, discard it.
5. **Consider forced alignment over transcription.** If you already have the verse text (which you do), forced alignment (CTC-based or DTW-based) avoids the hallucination problem entirely because it aligns known text rather than generating new text.

**Detection:** Look for repeated identical segments, known hallucination phrases, segments with very low `avg_logprob` but high duration, or transcribed text that doesn't appear in the chapter's verse list.

**Phase mapping:** Must be addressed in the alignment phase. This is the single biggest risk to output correctness.

---

### Pitfall 3: CTC Forced Alignment Drift on Long Audio

**What goes wrong:** CTC-based forced alignment (used by `ctc-forced-aligner`, WhisperX, wav2vec2) accumulates timing error over long audio files. By the end of a 30-minute chapter, timestamps can drift 3–5 seconds ahead of the actual speech. The drift is non-linear and unpredictable.

**Why it happens:** CTC models predict frame-level token probabilities. The Viterbi decoding finds the optimal path, but small per-frame errors compound over thousands of frames. The "peaky" CTC posterior distribution (non-blank tokens concentrated in narrow spikes) means the alignment is sensitive to model calibration. Academic research (BRCTC, LFA) confirms this is a fundamental limitation of vanilla CTC alignment.

**Consequences:** Early verses in a chapter have accurate timestamps; later verses are progressively more wrong. The error is invisible without manual verification — the JSONL output looks structurally valid.

**Prevention:**
1. **Chunk-and-align strategy:** Split each chapter audio into overlapping segments (e.g., 60-second windows with 5-second overlap). Align each chunk independently. Reset drift at chunk boundaries.
2. **Anchor to known boundaries:** Use VAD-detected silence regions (which often correspond to verse boundaries in narrated Bible text) as anchor points. Snap aligned timestamps to the nearest VAD boundary.
3. **Use segment-level alignment, not word-level:** Align at the verse level (each verse is one "segment") rather than word level. Fewer alignment points = less drift accumulation.
4. **Validate with spot checks:** For each chapter, manually verify 3–5 verse timestamps (beginning, middle, end). If drift exceeds a threshold (e.g., 500ms), re-align with different parameters.
5. **Consider aeneas (DTW-based)** for chapter-level alignment: DTW doesn't suffer from drift in the same way as CTC, though it has its own issues (see Pitfall 6).

**Detection:** Compare aligned timestamps at the end of a chapter against manual spot-checks. If the last verse's timestamp is consistently late, drift is occurring. Plot alignment offsets across the chapter — a monotonic trend indicates drift.

**Phase mapping:** Alignment phase. The alignment strategy must account for drift from the start.

---

### Pitfall 4: Catholic Bible Verse Numbering Mismatches

**What goes wrong:** The Szent István Társulat translation uses Catholic versification, which differs from Protestant/Hebrew numbering in several books. If your text source (szentiras.eu API) and audio source (mek.oszk.hu) use different versification systems, or if you try to validate against Protestant-oriented tools, verses won't line up.

**Why it happens:**
- **Psalms:** Hebrew numbering (used by Protestants) vs. Greek/Vulgate numbering (used by older Catholic editions). Through most of the Psalter, the Hebrew psalm number is one greater than the Greek. Modern Catholic translations (including SZIT) mostly follow Hebrew numbering, but edge cases remain (Ps 9/10, 114/115, 116, 147).
- **Psalm verse superscriptions:** Some traditions count the superscription as verse 1 (making all subsequent verses +1), others don't. The NAB counts superscriptions; most Protestant translations don't.
- **Deuterocanonical books:** Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees, plus additions to Daniel and Esther — ~6,927 verses that don't exist in Protestant Bibles. Many Bible tools, APIs, and reference systems don't include them.
- **Verse splits/merges:** Some translations combine what others split (e.g., Ps 147:11-12). Numbers 25:19 in NAB is Numbers 26:1 in most other Bibles.
- **Deuteronomy/Joel/Malachi:** Chapter-verse boundaries shift between Hebrew and Greek systems (e.g., Dt 12:32 Hebrew = Dt 13:1 Greek).

**Consequences:** Your JSONL output references verses that don't exist in the audio, or maps audio to the wrong verse. Cross-validation against external tools fails. Downstream consumers using standard OSIS/USX references get confused.

**Prevention:**
1. **Use a single versification authority:** The szentiras.eu API's SZIT translation is your canonical verse reference. All verse IDs in your JSONL must match this source exactly.
2. **Build a versification mapping table:** Map SZIT verse references to USX codes (already provided by szentiras.eu GitHub repo: `tdverse` table with `trans`, `gepi`, `usx_code`). Validate that every verse in your text source has a corresponding audio segment.
3. **Handle deuterocanonical books explicitly:** Verify that the mek.oszk.hu audio includes all 73 Catholic books. If audio is missing for deuterocanonicals, flag those books as "text-only" in your output.
4. **Never assume verse counts match:** For each chapter, compare the number of verses in the text source against the number of verse-aligned audio segments. Mismatches indicate versification problems.
5. **Test with known problem books:** Psalms, Daniel (additions), Esther (additions), Numbers 25-26.

**Detection:** Verse count mismatch between text source and expected audio segments. USX codes that don't resolve. Gaps in verse numbering (e.g., jumping from verse 14 to 16).

**Phase mapping:** Text parsing phase (build the mapping table) and alignment phase (validate counts).

---

### Pitfall 5: Hungarian ASR Accuracy Is Insufficient for Naive Transcription

**What goes wrong:** Using Whisper (even fine-tuned Hungarian models) for raw transcription produces Word Error Rates of 7–25% depending on the model. At 15% WER on a chapter with 500 words, ~75 words are wrong. Fuzzy matching these against verse text fails for morphologically similar but semantically different words — especially problematic in Hungarian's agglutinative morphology where a single suffix change alters meaning.

**Why it happens:**
- Hungarian is a low-resource language for ASR. Base Whisper large-v2 achieves ~26% WER on Common Voice Hungarian. Fine-tuned models reach ~7-9% WER on clean test sets, but Bible narration may differ acoustically from training data.
- Hungarian is agglutinative: "ház" (house), "házban" (in the house), "házainkban" (in our houses) are all valid words. ASR errors in suffixes produce valid Hungarian words that fuzzy-match but are wrong.
- Proper nouns (biblical names: "Nabukodonozor", "Nehemiás", "Szefóniás") are particularly error-prone.
- Archaic/literary register of Bible text differs from conversational Hungarian in training data.

**Consequences:** Transcription-based alignment (transcribe → fuzzy match → timestamp) produces incorrect verse boundaries. The errors are subtle — the matched verse is "close" but wrong.

**Prevention:**
1. **Don't use ASR for alignment — use forced alignment.** You have the ground-truth text. Use CTC-based forced alignment (wav2vec2 + Viterbi) or DTW-based alignment (aeneas) to align known text to audio, rather than transcribing and matching.
2. **If you must use Whisper (e.g., for validation):** Use `sarpba/whisper-hu-large-v3-turbo-finetuned` (7.5% WER) or `Maxdorger/whisper-hungarian-lora` (LoRA fine-tuned, fixes hallucinations). Run on GPU (3090 is sufficient).
3. **Normalize before matching:** Strip diacritics, lowercase, remove punctuation before fuzzy matching. Use character-level edit distance, not word-level.
4. **Use Whisper only for validation, not primary alignment:** Align with forced alignment, then transcribe with Whisper and compare. Discrepancies flag suspect alignments.

**Detection:** High edit distance between transcribed text and expected verse text. Systematic errors in specific word categories (proper nouns, archaic forms).

**Phase mapping:** Alignment phase — the choice between transcription+matching vs. forced alignment is the central architectural decision.

---

## Moderate Pitfalls

Mistakes that cause significant rework or degraded output quality.

### Pitfall 6: Aeneas DTW Alignment Quality Depends on TTS Quality for Hungarian

**What goes wrong:** aeneas uses a TTS+DTW approach: it synthesizes the text with eSpeak, then uses Dynamic Time Warping to match synthesized audio against real audio. If eSpeak's Hungarian pronunciation is poor, the DTW cost matrix is noisy and alignment degrades — especially for long verses or verses with unusual words.

**Why it happens:** aeneas's language dependence is entirely through the TTS engine. eSpeak's Hungarian voice is robotic and may mispronounce biblical proper nouns, archaic forms, and compound words. The DTW algorithm is robust but not magic — if the synthesized audio sounds nothing like the real audio, alignment fails.

**Consequences:** Alignment accuracy degrades for books with many proper nouns (Genesis genealogies, Chronicles, Acts). Verses with long compound Hungarian words may be misaligned.

**Prevention:**
1. **Test aeneas on a sample chapter first** before committing to it as the alignment strategy. Pick a chapter with diverse content (narrative, poetry, proper nouns).
2. **Pre-process text for aeneas:** Replace archaic spellings with modern equivalents, simplify proper nouns to phonetic approximations if needed.
3. **Use aeneas at the verse level (not word level):** aeneas works best when text fragments are 1-3 sentences. Verse-level alignment (each verse = one fragment) is the sweet spot.
4. **Consider a hybrid approach:** Use aeneas for coarse chapter-level or section-level alignment, then refine within sections using CTC-based alignment or silence detection.
5. **Evaluate the `cew` C extension:** aeneas with the compiled C extension (`cew`) produces significantly better results than the pure Python fallback. Ensure it's installed.

**Detection:** Alignment quality degrades systematically for certain books or chapters. Manual spot-checks show consistent offsets in proper-noun-heavy passages.

**Phase mapping:** Alignment phase — evaluate aeneas early as a candidate.

---

### Pitfall 7: MP3 Encoder Delay and Padding

**What goes wrong:** All MP3 encoders add padding at the beginning (encoder delay: 576 samples for LAME, 528 for ISO encoders) and end (padding: 288+ samples) of the file. Decoders add their own delay (528 samples). The net effect is that decoded audio starts 1056–2256 samples later than the original — roughly 24–51ms at 44.1kHz. This offset is consistent within a file but varies between files depending on encoder.

**Why it happens:** MP3 uses MDCT (Modified Discrete Cosine Transform), which requires overlapping frames. The first frame has no previous frame to overlap with, so encoders add silent padding. The LAME tag stores the exact delay/padding values, but not all decoders honor them.

**Consequences:** Timestamps from alignment are offset by a constant amount from the "true" start of speech. For verse-level alignment (where precision of ~200ms is acceptable), this is minor. For word-level alignment, it's significant.

**Prevention:**
1. **Use `ffmpeg` for decoding** — it handles LAME gapless playback correctly when the LAME tag is present.
2. **Measure the offset:** Decode the first chapter's MP3 to WAV, check for leading silence, and measure its duration. If consistent across files, apply a global offset correction.
3. **Store the offset in metadata:** Include `encoder_delay_ms` in your JSONL output so downstream consumers can compensate.

**Detection:** Decoded WAV files start with 20–50ms of silence before speech begins.

**Phase mapping:** Audio preprocessing phase.

---

### Pitfall 8: Text Source Fragility (API + HTML Scraping)

**What goes wrong:** The szentiras.eu API requires an API key (email maintainers), may have rate limits, and could change endpoints without notice. The mek.oszk.hu HTML fallback is a scraping target — HTML structure changes break parsers silently, returning empty or corrupted data.

**Why it happens:** szentiras.eu is a community project, not a commercial API with SLAs. mek.oszk.hu is a national library archive — stable but not designed for programmatic access. Neither provides versioned APIs or change notifications.

**Consequences:** Your data pipeline breaks without warning. Worse, silent data corruption: the scraper returns data that looks valid but is missing verses, has wrong chapter boundaries, or contains HTML artifacts in the text.

**Prevention:**
1. **Cache aggressively:** Download the full Bible text once and store locally. Re-fetch only on explicit command (Taskfile task: `download-text`). Never fetch during alignment.
2. **Validate completeness:** After download, verify verse counts per book/chapter against the known schema (73 books, expected verse counts from `tdverse` table). Flag any chapter with fewer verses than expected.
3. **Checksum your data:** Store SHA-256 of downloaded text files. Detect silent changes on re-download.
4. **Cross-validate sources:** Compare API text against HTML-scraped text. Any divergence is a data quality issue that must be resolved before alignment.
5. **Handle encoding correctly:** mek.oszk.hu may serve Latin-2 encoded content. Ensure your parser handles charset detection and converts to UTF-8.

**Detection:** Verse count mismatches between sources. Empty or truncated responses. Encoding errors (mojibake) in downloaded text.

**Phase mapping:** Text download/parsing phase. Must be solid before alignment begins.

---

### Pitfall 9: Alignment Confidence Calibration

**What goes wrong:** Your JSONL output includes a `confidence` field, but there's no ground truth to calibrate it against. Without calibration, confidence scores are meaningless — a "high confidence" alignment might be wrong, and a "low confidence" one might be correct. Downstream consumers can't use confidence for filtering.

**Why it happens:** Forced alignment algorithms produce internal scores (CTC posterior probabilities, DTW cost values), but these are not directly interpretable as "probability the alignment is correct." The relationship between internal score and actual accuracy varies by audio quality, speaker, and content.

**Consequences:** Users filter by confidence and either keep bad alignments (threshold too low) or discard good ones (threshold too high). The confidence field becomes decorative.

**Prevention:**
1. **Define confidence operationally:** e.g., "confidence = fuzzy match score between aligned audio segment (transcribed by Whisper) and expected verse text." This is measurable and interpretable.
2. **Create a small gold-standard set:** Manually align 50–100 verses across diverse chapters. Use this to calibrate confidence thresholds (e.g., "score > 0.8 = correct 95% of the time").
3. **Use multiple signals:** Combine CTC posterior score + Whisper transcription match + VAD boundary proximity into a composite confidence score.
4. **Be honest about uncertainty:** If you can't calibrate, label the field as `alignment_score` (not `confidence`) and document what it measures.

**Detection:** Downstream users report that filtering by confidence doesn't improve results. Manual spot-checks show no correlation between confidence and accuracy.

**Phase mapping:** Alignment phase (design) and export phase (calibration).

---

### Pitfall 10: Deuterocanonical Books Missing from Audio or Tools

**What goes wrong:** The mek.oszk.hu audio collection may not include all 7 deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees) or the additions to Daniel and Esther. Many Bible software tools, reference systems, and APIs are Protestant-oriented and lack these books entirely.

**Why it happens:** The audio recordings at mek.oszk.hu (ID 08800/08820) may be a complete Catholic Bible or may omit deuterocanonicals. This needs to be verified. Many Bible tech tools (OSIS parsers, USX code libraries) default to 66-book Protestant canons.

**Consequences:** Your pipeline crashes or produces incomplete output for 7+ books (~6,927 verses). The Catholic Bible has 73 books — if your tooling assumes 66, you lose ~10% of the Old Testament.

**Prevention:**
1. **Verify audio availability first:** Before building the pipeline, manually check mek.oszk.hu/08800/08820/mp3/ for all 73 books. List which books have audio and which don't.
2. **Build the book list from szentiras.eu:** The API lists all books including "Deuterokanonikus könyvek (7)" — Tóbiás, Judit, Bölcsesség, Sirák, Báruk, 1. Makkabeusok, 2. Makkabeusok.
3. **Handle missing audio gracefully:** For books without audio, produce JSONL entries with `audio_file: null` and `confidence: 0` rather than omitting them.
4. **Use Catholic-aware reference systems:** The szentiras.eu GitHub repo has the full 73-book schema with Hungarian abbreviations and USX codes. Use this as your canonical book list.

**Detection:** Pipeline processes only 66 books. Deuterocanonical book abbreviations not found in reference data. Audio file list shorter than expected.

**Phase mapping:** Data download phase (verify audio availability) and text parsing phase (ensure 73-book schema).

---

## Minor Pitfalls

Issues that are annoying but fixable without rewrites.

### Pitfall 1: Chapter Boundary Audio Content

**What goes wrong:** Per-chapter MP3 files may include non-verse audio: chapter title announcements ("Első fejezet"), section headings read aloud, introductory text, or closing remarks. These segments don't correspond to any verse and will confuse alignment.

**Prevention:** Detect and skip non-verse segments. Use VAD to find speech regions, then check if the transcribed text matches any verse. Unmatched speech at the beginning/end of a chapter is likely introductory/concluding material.

---

### Pitfall 2: Hungarian Diacritics and Text Normalization

**What goes wrong:** Hungarian uses extensive diacritics (á, é, í, ó, ö, ő, ú, ü, ű). Text sources may use different encoding (Latin-2 vs UTF-8), different normalization forms (NFC vs NFD), or inconsistent double-accent characters (ő vs ö + combining accent). Fuzzy matching fails if normalization differs between text source and ASR output.

**Prevention:** Normalize all text to NFC UTF-8 at ingestion. Use `unicodedata.normalize('NFC', text)` in Python. Strip diacritics only for fuzzy matching (not for storage).

---

### Pitfall 3: Narrator-Specific Pacing and Pauses

**What goes wrong:** Different narrators have different pacing. Some pause significantly between verses (2-3 seconds), others barely pause. Some read section headings, others skip them. Alignment parameters tuned for one narrator may not work for another.

**Prevention:** Design the pipeline to be narrator-aware. Store narrator ID in metadata. Allow per-narrator configuration of pause thresholds and alignment parameters. For v1 (single narrator), document the narrator's characteristics.

---

### Pitfall 4: Audio File Naming and Ordering

**What goes wrong:** mek.oszk.hu MP3 filenames may not follow a predictable pattern that maps to book/chapter. Files might be named by sequential number, by Hungarian book name, or by some other scheme. Incorrect mapping between audio files and book/chapter references corrupts the entire output.

**Prevention:** Download the file listing first and manually map each filename to a book/chapter reference. Store this mapping as a configuration file. Validate by checking that the number of audio files matches the expected number of chapters.

---

### Pitfall 5: Large File Processing Memory Issues

**What goes wrong:** Some Bible chapters produce very long audio files (Psalms, Isaiah, Jeremiah can be 30-60+ minutes). Loading full audio into memory for alignment can exceed available RAM, especially with CTC models that need GPU memory for the model AND the audio tensor.

**Prevention:** Process audio in chunks (the `ctc-forced-aligner` supports `--window_size` and `--context_size` parameters). Use streaming audio loading (librosa with `duration` parameter) rather than loading entire files. The 3090's 24GB VRAM is generous but not unlimited.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Text download | API key not available or rate-limited | Have HTML fallback ready; cache aggressively |
| Text parsing | Verse numbering mismatch between sources | Build versification mapping table; validate counts |
| Audio download | Missing deuterocanonical books | Verify all 73 books before pipeline design |
| Audio preprocessing | VBR MP3 seek inaccuracy | Decode to WAV before any timestamp work |
| Alignment strategy | Choosing wrong approach (transcription vs forced alignment) | Prototype both on 3 sample chapters; measure accuracy |
| Alignment execution | CTC drift on long chapters | Chunk-and-align with VAD anchoring |
| Alignment execution | Whisper hallucination on pauses | VAD pre-filtering; never trust raw Whisper output |
| Alignment validation | No ground truth for calibration | Manually align 50-100 verses as gold standard |
| Export | Confidence scores meaningless | Define confidence operationally; calibrate against gold standard |
| Backup | Data loss before backup is configured | Set up rsync backup before any large processing runs |

## Sources

- ExoPlayer MP3 seeking issues: https://github.com/google/ExoPlayer/issues/6787 (HIGH confidence — official issue tracker)
- VBR MP3 seeking explanation: https://valor-software.com/articles/diving-into-seeking-issue-with-mp3-files (MEDIUM confidence — technical blog)
- LAME encoder delay/padding: https://lame.sourceforge.io/tech-FAQ.txt (HIGH confidence — official documentation)
- Whisper hallucination on silence: https://github.com/openai/whisper/discussions/1606, https://github.com/openai/whisper/pull/1838 (HIGH confidence — official repo)
- CTC forced alignment drift: https://openreview.net/pdf?id=JpG7RsIFhL (LFA paper, HIGH confidence — peer-reviewed)
- CTC peaky behavior and label priors: https://arxiv.org/html/2406.02560v3 (HIGH confidence — peer-reviewed)
- ctc-forced-aligner drift issues: https://github.com/MahmoudAshraf97/ctc-forced-aligner/issues/84 (MEDIUM confidence — user reports)
- WhisperX Hungarian wav2vec2 model: `jonatasgrosman/wav2vec2-large-xlsr-53-hungarian` in source code (HIGH confidence — verified in codebase)
- Hungarian Whisper WER benchmarks: https://huggingface.co/sarpba/whisper-teszt-eredmenyek (MEDIUM confidence — community benchmarks)
- Hungarian fine-tuned Whisper: https://huggingface.co/sarpba/whisper-hu-large-v3-turbo-finetuned (7.5% WER, MEDIUM confidence)
- LoRA Hungarian Whisper: https://github.com/Maxdorger/whisper-hungarian-lora (MEDIUM confidence — community project)
- Catholic vs Protestant Bible differences: https://catholicbibleonline.com/blog/differences-catholic-protestal-bibles-complete-guide/ (MEDIUM confidence)
- Psalm numbering systems: https://welovegod.org/guide/psalmnumbering/ (MEDIUM confidence)
- OT verse numbering differences: http://catholicbibles.blogspot.com/2015/06/guest-post-old-testament-verse.html (MEDIUM confidence)
- Catholic OT statistics: https://catholic-resources.org/Bible/OT-Statistics-NAB.htm (HIGH confidence — academic source)
- Bible versification comparison: https://matthewbarron.org/bible-versification-compared/ (MEDIUM confidence)
- aeneas forced alignment: https://github.com/readbeyond/aeneas/ (HIGH confidence — official repo)
- aeneas DTW algorithm: https://github.com/readbeyond/aeneas/blob/master/wiki/HOWITWORKS.md (HIGH confidence — official docs)
- aeneas quality issues: https://github.com/readbeyond/aeneas/issues/301, https://github.com/readbeyond/aeneas/issues/295 (MEDIUM confidence — user reports)
- Forced aligners benchmark: https://github.com/PalabraAI/forced-aligners-bench (MEDIUM confidence — community benchmark)
- Scripture App Builder aeneas guide: https://software.sil.org/downloads/r/scriptureappbuilder/ (MEDIUM confidence — SIL International)
- Bible ASR limitations: https://aclanthology.org/2025.ijcnlp-short.28.pdf (HIGH confidence — peer-reviewed)
- Scraping vs API stability: https://holybible.dev/compare/biblebridge-vs-scraping-bible-websites (MEDIUM confidence)
- szentiras.eu structure: https://szentiras.eu/index.php (verified — live site)
- mek.oszk.hu metadata: https://mek.oszk.hu/html/lod_eng.html (HIGH confidence — official site)
- Hungarian ASR datasets: https://arxiv.org/html/2511.13529v2 (HIGH confidence — peer-reviewed)
