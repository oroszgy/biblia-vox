---
phase: 03-audio-pipeline
reviewed: 2026-05-29T21:08:40Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - bibliavox/audio/discovery.py
  - bibliavox/audio/downloader.py
  - bibliavox/audio/convert.py
  - bibliavox/audio/metadata.py
  - bibliavox/audio/seek_index.py
  - bibliavox/audio/pipeline.py
  - bibliavox/audio/__init__.py
  - bibliavox/cli/audio.py
  - bibliavox/main.py
  - Taskfile.yml
  - tests/test_audio_discovery.py
  - tests/test_audio_downloader.py
  - tests/test_audio_convert.py
  - tests/test_audio_metadata.py
  - tests/test_audio_seek_index.py
  - tests/test_audio_pipeline.py
  - tests/test_audio_cli.py
findings:
  critical: 3
  warning: 2
  info: 0
  total: 5
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-29T21:08:40Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Reviewed all Phase 3 audio-pipeline files in scope with adversarial focus on correctness and security. I found three shipping blockers (two path-safety issues in `audio seek`, one data-corruption bug in downloader retry flow) plus two robustness warnings.

## Critical Issues

### CR-01 (BLOCKER): Relative `--output` path traversal in `audio seek`

**File:** `bibliavox/cli/audio.py:59-68, 292, 305, 318-323`

**Issue:** `_validate_seek_output_path()` only restricts **absolute** output paths. Relative paths are accepted without containment checks. A user can pass `--output ../../somewhere.wav` and write outside `prepared_root`, bypassing the intended boundary.

**Fix:** Resolve relative paths against `prepared_root` (or cwd, but then enforce containment) and validate all outputs, not just absolute ones.

```python
def _validate_seek_output_path(output_path: Path, prepared_root: Path) -> Path:
    resolved_root = prepared_root.resolve()
    candidate = output_path if output_path.is_absolute() else (resolved_root / output_path)
    candidate = candidate.resolve()

    allowed_roots = [resolved_root, Path("/tmp").resolve()]
    if not any(candidate.is_relative_to(root) for root in allowed_roots):
        raise SeekIndexError(
            "Output path is restricted to prepared root or /tmp"
        )
    return candidate
```

### CR-02 (BLOCKER): Untrusted `wav_path` from index enables arbitrary file read attempt

**File:** `bibliavox/cli/audio.py:306-313, 318-323`

**Issue:** `seek` trusts `index_payload["wav_path"]` and passes it directly to `write_seek_preview()` without root/allowlist checks. A crafted index JSON can point to arbitrary local files. If readable as WAV, this leaks data into attacker-chosen preview output.

**Fix:** Validate `wav_path` is within `prepared_root` (or a strict allowlist) before reading.

```python
wav_path = Path(str(index_payload["wav_path"]))
resolved_wav = wav_path.resolve()
resolved_root = prepared_root.resolve()
if not resolved_wav.is_relative_to(resolved_root):
    raise SeekIndexError("Invalid seek index: wav_path must be under prepared root")
```

### CR-03 (BLOCKER): Retry logic can corrupt resumed downloads

**File:** `bibliavox/audio/downloader.py:37-48, 79, 89`

**Issue:** `resume_from` is computed once in `download_chapter()` and passed into `_stream_download()`, which is retried by Tenacity. If a retry happens after partial bytes were appended, subsequent attempts still request the original `Range` offset and append again, duplicating bytes and corrupting the resulting MP3.

**Fix:** Recompute resume offset per retry attempt (inside retry-wrapped function), or remove internal retry and perform retries at `download_chapter()` level while recalculating `part_path.stat().st_size` each attempt.

```python
@retry(...)
def _stream_download(client: Any, url: str, part_path: Path) -> None:
    resume_from = part_path.stat().st_size if part_path.exists() else 0
    headers = {"Range": f"bytes={resume_from}-"} if resume_from > 0 else {}
    ...
```

## Warnings

### WR-01 (WARNING): ffmpeg timeout escapes as uncaught exception type

**File:** `bibliavox/audio/convert.py:57-63, 65-69`

**Issue:** `subprocess.run(..., timeout=...)` may raise `subprocess.TimeoutExpired`, but `convert_to_wav()` does not catch/wrap it in `AudioConversionError`. CLI handlers catch `AudioConversionError`, so timeout paths can bubble as unexpected exceptions instead of controlled CLI failures.

**Fix:** Catch `TimeoutExpired` and raise `AudioConversionError` with clear context.

```python
try:
    process = subprocess.run(..., timeout=CONVERSION_TIMEOUT_SECONDS)
except subprocess.TimeoutExpired as exc:
    raise AudioConversionError(
        f"ffmpeg timed out after {CONVERSION_TIMEOUT_SECONDS}s for {input_mp3}"
    ) from exc
```

### WR-02 (WARNING): `prepare_chapter` skip path trusts existence, not validity

**File:** `bibliavox/audio/pipeline.py:55-61`

**Issue:** Skip logic only checks that WAV/meta/index files exist; it does not validate JSON parseability, required fields, or that sidecars match the target chapter/book. Corrupted or stale artifacts can be silently treated as valid.

**Fix:** On skip path, minimally validate metadata/index schema and consistency (`book_usx`, `chapter`, `wav_path`) before returning `status="skipped"`; otherwise rebuild.

```python
if wav_path.exists() and meta_path.exists() and index_path.exists() and not force:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        idx = json.loads(index_path.read_text(encoding="utf-8"))
        if meta.get("book_usx") == normalized_book and meta.get("chapter") == chapter and Path(idx.get("wav_path", "")) == wav_path:
            return PrepareChapterResult(..., status="skipped")
    except (OSError, ValueError):
        pass
    # fall through to rebuild
```

---

_Reviewed: 2026-05-29T21:08:40Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
