# Codebase Concerns

**Analysis Date:** 2026-06-02

## Critical Blockers (Phase 5)

**SZTAKI-HLT/hubert-base-cc is text BERT, not audio HuBERT:**
- Issue: `SZTAKI-HLT/hubert-base-cc-hu` is configured in the model gauntlet but is a Hungarian text BERT model (RoBERTa-based), NOT an audio/speech model. It will crash the audio transcription pipeline because it expects text tokens, not audio waveforms.
- Files: `bibliavox/config.py:36`, `bibliavox/align/transcribe.py:61-94`
- Impact: Running the gauntlet with this model will fail at inference time. The VibeVoice code path in `transcribe.py` will attempt to load it as a speech model.
- Fix approach: Replace with `facebook/mms-1b-fl102` (forced alignment, 2.2GB VRAM) or `sarpba/wav2vec2-large-xlsr-53-hungarian` (CTC alignment, 1.5GB VRAM). Update `ModelGauntletSettings` in `config.py`.

**Hungarian Whisper LoRA performance unverified:**
- Issue: `bofenghuang/whisper-large-v2-cv11-hu` is a gated model on HuggingFace. The code silently falls back to `large-v2` when unavailable (`bibliavox/align/transcribe.py:30-34`). Performance on Bible narration (literary register) is unknown.
- Files: `bibliavox/align/transcribe.py:30-34`, `bibliavox/config.py:37`
- Impact: Evaluation results may not reflect actual Hungarian Bible transcription quality. The fallback model is generic multilingual Whisper, not Hungarian-tuned.
- Fix approach: Test with `systran/faster-whisper-large-v3` (Apache 2.0, excellent multilingual) as primary ASR. Document fallback behavior explicitly rather than silently switching models.

## Security Considerations

**Path traversal vulnerability (OPEN threat T25-DQ-04):**
- Risk: CLI commands accept arbitrary `--output` paths with no allowlist or repo-root confinement. A user could write artifacts outside the project directory.
- Files: `bibliavox/cli/text.py:331-359`, `bibliavox/text/jsonl_converter.py:42`, `bibliavox/text/splitter.py:182`
- Current mitigation: None — paths are passed directly to `open()`.
- Recommendations: Add path validation to confine writes under `data/` or `/tmp`. See SECURITY.md for full threat register.

**Non-atomic file writes (OPEN threat T25-DQ-05):**
- Risk: All JSONL writers use direct `open(..., "w")` without temp-file + atomic rename. Interruption during write produces corrupt/partial artifacts.
- Files: `bibliavox/text/jsonl_converter.py:42`, `bibliavox/text/splitter.py:182`, `bibliavox/cli/align.py:56,124,265,340`, `bibliavox/text/mek_source.py:269`
- Current mitigation: None.
- Recommendations: Implement temp-file + `os.replace()` pattern for all artifact writes.

**Malformed JSONL causes hard-fail (OPEN threat T25-DQ-06):**
- Risk: `fix_verses` in `splitter.py` reads lines with `json.loads(line)` (line 101) with no error handling. One malformed line aborts the entire run.
- Files: `bibliavox/text/splitter.py:99-103`
- Current mitigation: None — unlike `cross_validator.py:42` which handles `JSONDecodeError` gracefully.
- Recommendations: Add try/except around `json.loads` with line-level error reporting, matching the pattern in `cross_validator.py`.

**ast.literal_eval on external data:**
- Risk: `load_szit_json` uses `ast.literal_eval()` as first-parsing-attempt on downloaded external content (`bibliavox/text/source.py:51`). While safer than `eval()`, it still executes Python literal expressions.
- Files: `bibliavox/text/source.py:49-54`
- Current mitigation: Falls back to `json.loads` if `literal_eval` fails. The SZIT JSON file uses Python literal format (single quotes).
- Recommendations: Pre-validate or convert the SZIT JSON to standard JSON format to eliminate `literal_eval` entirely.

## Code Quality Issues

**Broad exception handling:**
- Issue: Multiple locations catch bare `Exception` which masks specific error types and makes debugging harder.
- Files: `bibliavox/cli/align.py:60,236,366`, `bibliavox/text/mek_source.py:292`, `bibliavox/coverage.py:180`, `bibliavox/audio/downloader.py:97`
- Impact: Errors are caught and either silently skipped or reported generically. Root causes become harder to trace.
- Fix approach: Catch specific exception types. Where broad catches are intentional (e.g., resilient download), add `noqa: BLE001` comments and log the full traceback.

**Module-level singletons with global mutable state:**
- Issue: Four modules use module-level singleton caches with `global` keyword mutation.
- Files: `bibliavox/config.py:81-103` (`_settings`), `bibliavox/text/source.py:17-39` (`_SZIT_DATA`), `bibliavox/text/mapping.py:102` (`_MAPPING`), `bibliavox/reference/schema.py:75` (`_SCHEMAS`), `bibliavox/reference/books.py:86` (`_BOOKS`)
- Impact: State leaks between tests (mitigated by `reset_settings()` but only for config). Other singletons have no reset mechanism, making test isolation fragile.
- Fix approach: Add `reset_*()` functions for all cached singletons, or use dependency injection.

**Silent model fallback without user notification:**
- Issue: When `bofenghuang/whisper-large-v2-cv11-hu` is unavailable, the code silently falls back to `large-v2` with only a `logger.warning` (`bibliavox/align/transcribe.py:30-34`). The CLI user sees no indication that a different model was used.
- Files: `bibliavox/align/transcribe.py:30-34`
- Impact: Evaluation results may be misattributed to the wrong model.
- Fix approach: Surface model fallback in CLI output and evaluation reports.

## Performance Bottlenecks

**Full corpus loaded into memory:**
- Problem: `splitter.py:fix_verses` loads the entire JSONL file into memory grouped by chapter (line 98-103). `cross_validator.py:load_jsonl_corpus` loads both SZIT and MEK corpora fully into memory.
- Files: `bibliavox/text/splitter.py:97-103`, `bibliavox/text/cross_validator.py:16-46`
- Cause: In-memory grouping requires full file load. For 35,350 verses across 73 books, this is manageable but does not scale.
- Improvement path: For splitter, use streaming with chapter-boundary detection. For cross-validator, the in-memory approach is acceptable for v1 (finite corpus size).

**Docker dependency installation on every build:**
- Problem: `Dockerfile.align` uses `pip install` without caching layer for dependencies. Every `docker compose build` reinstalls all packages.
- Files: `docker/Dockerfile.align:15-29`
- Cause: No `requirements.txt` or lockfile for Docker pip install. Dependencies are listed inline.
- Improvement path: Generate a `requirements-docker.txt` from pyproject.toml, use `COPY requirements-docker.txt .` + `RUN pip install` before `COPY . .` to leverage Docker layer caching.

## Fragile Areas

**Alignment module (`bibliavox/align/`):**
- Files: `bibliavox/align/transcribe.py`, `bibliavox/align/match.py`
- Why fragile: The `transcribe.py` module has hardcoded fallback logic for specific model IDs (line 30-34) and type-based branching (faster-whisper vs vibevoice) with different output formats. The `match.py` module assumes word transcripts have consistent structure.
- Safe modification: Add input validation for transcript format. Extract model-specific logic into separate strategy classes.
- Test coverage: Tests use heavy module-level mocking (`test_align.py:5-9` mock `faster_whisper` and `transformers` modules). No integration tests verify actual model loading or inference.

**Reference data generation (`bibliavox/reference/generate.py`):**
- Files: `bibliavox/reference/generate.py` (779 lines — largest source file)
- Why fragile: Contains hardcoded `BOOK_METADATA` and `BOOK_NUMBERS` dicts with 73 book entries. Any schema change requires manual updates to multiple data structures.
- Safe modification: Validate generated output against versification schema. Add snapshot tests for generated JSON.
- Test coverage: Tests exist (`test_generate.py`, `test_cli_reference.py`) but do not verify all 73 books are generated correctly.

## Dependencies at Risk

**Docker base image `pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime`:**
- Risk: PyTorch 2.3.0 is outdated (current: 2.6+). May have known bugs or security issues.
- Impact: Model inference correctness or performance may differ from newer versions.
- Migration plan: Update to latest PyTorch LTS when Phase 5 alignment testing begins.

**`bofenghuang/whisper-large-v2-cv11-hu` (gated model):**
- Risk: Model is gated on HuggingFace and may require acceptance of terms. Code already has fallback but the primary model is unreliable.
- Impact: Evaluation pipeline cannot use the intended Hungarian-tuned model.
- Migration plan: Use `systran/faster-whisper-large-v3` as primary, remove gated model from default gauntlet.

**`faster-whisper` (Docker-only dependency):**
- Risk: Not in `pyproject.toml` dependencies — only installed in Docker. Local development cannot run alignment without Docker.
- Impact: Developers must use Docker for all alignment work. No lightweight local testing path.
- Migration plan: Add `faster-whisper` as optional dependency group in pyproject.toml for local GPU development.

## Test Coverage Gaps

**No coverage enforcement:**
- What's not tested: `pytest-cov` is not in dev dependencies. No coverage thresholds are enforced.
- Files: `pyproject.toml` (missing `pytest-cov` from dev deps)
- Risk: Coverage regression goes undetected.
- Priority: Medium

**Alignment tests use heavy mocking:**
- What's not tested: `test_align.py` mocks `faster_whisper` and `transformers` at module level (lines 5-9). No integration test verifies actual model loading, transcription, or matching on real audio.
- Files: `tests/test_align.py:1-9`
- Risk: Mock tests pass but actual model inference may fail due to API changes, missing dependencies, or model format issues.
- Priority: High — Phase 5 depends on this working.

**No test for `coverage.py` remote manifest fetch:**
- What's not tested: `_fetch_remote_manifest()` makes a live HTTP request to mek.oszk.hu. Tests mock this but no integration test verifies the M3U playlist is still accessible and parseable.
- Files: `bibliavox/coverage.py:125-130`, `tests/test_coverage.py`
- Risk: Remote M3U format change would break coverage audit silently.
- Priority: Low

**No test for `generate.py` full book generation:**
- What's not tested: `write_books_json` and `write_versification_json` are tested but not for all 73 books. Missing books would not be detected.
- Files: `bibliavox/reference/generate.py:703-737`, `tests/test_generate.py`
- Risk: Schema changes or missing book metadata could produce incomplete reference data.
- Priority: Medium

## Documentation Gaps

**No Phase 5 planning documents:**
- Issue: `.planning/phases/05-forced-alignment/` directory does not exist. Phase 4 research documents recommended models but no Phase 5 plan exists.
- Files: `.planning/phases/` (missing `05-forced-alignment/`)
- Impact: Phase 5 execution lacks structured guidance on which forced alignment models to implement, test, and compare.
- Priority: High — blocks Phase 5 execution.

**SECURITY.md not updated since Phase 2.5:**
- Issue: Security audit covers only text pipeline components. Audio pipeline and alignment modules are not audited.
- Files: `SECURITY.md` (last updated Phase 2.5)
- Impact: New attack surfaces in audio download, conversion, and alignment are undocumented.
- Priority: Medium

## Technical Debt Markers

**Hardcoded gold chapters in evaluate-gold command:**
- Issue: `GOLD_CHAPTERS` list is hardcoded in `bibliavox/cli/align.py:142-153`. Changing evaluation chapters requires code modification.
- Files: `bibliavox/cli/align.py:142-153`
- Fix approach: Move to configuration file or CLI option with default fallback.

**Inconsistent error reporting in CLI:**
- Issue: Some commands use `console.print` + `raise typer.Exit(1)`, others use `typer.echo`. Error message formatting is inconsistent (some use Rich markup, others plain text).
- Files: `bibliavox/cli/align.py`, `bibliavox/cli/text.py`, `bibliavox/cli/audio.py`
- Fix approach: Standardize on Rich console for all CLI output with consistent error styling.

**No JSONL schema validation:**
- Issue: JSONL records are written and read with implicit schema (book, chapter, verse, text keys). No schema validation on read or write.
- Files: `bibliavox/text/jsonl_converter.py`, `bibliavox/text/splitter.py`, `bibliavox/text/cross_validator.py`
- Fix approach: Define Pydantic model for JSONL records and validate on read.

---

*Concerns audit: 2026-06-02*
