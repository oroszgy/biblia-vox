---
phase: 07-export-and-pipeline-integration
reviewed: 2026-06-02T20:44:40Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - bibliavox/cli/export.py
  - bibliavox/config.py
  - bibliavox/export/__init__.py
  - bibliavox/export/writer.py
  - bibliavox/main.py
  - Taskfile.yml
  - tests/test_config.py
  - tests/test_export_writer.py
  - tests/test_pipeline_integration.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-06-02T20:44:40Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the Phase 7 export pipeline implementation: CLI subcommand (`bibliavox export jsonl`), config extension (gold chapters), JSONL writer module, Taskfile targets, and tests. The overall architecture is sound — Pydantic Settings integration, Rich progress bars, canonical text join from mek.jsonl, and confidence normalization are all well-structured. However, the writer module has a critical data corruption bug in its file write mode, and the CLI has a path computation issue that produces incorrect metadata when `BIBLIAVOX_DATA_DIR` is overridden. Error handling in the writer is also thin for production use.

## Critical Issues

### CR-01: Append mode causes data duplication with `--force`

**File:** `bibliavox/export/writer.py:127`
**Issue:** `export_chapter_jsonl` unconditionally opens the output file in append mode (`"a"`). When `--force` is used to re-export a chapter, new rows are appended to the existing file instead of replacing it. This produces duplicate verse entries in the JSONL, corrupting the output. The integration test `test_export_jsonl_force_overwrites_complete` (line 188-192) actually verifies this buggy behavior as expected — it asserts `final_line_count > first_line_count` after `--force`, confirming the duplication.
**Fix:**
```python
# bibliavox/export/writer.py, line 127
# Change from append to write mode — the caller (CLI) already handles
# idempotency checks, so the writer should overwrite, not append.
    with open(output_file, "w", encoding="utf-8") as out:
```
And update the integration test to verify replacement instead of accumulation:
```python
# tests/test_pipeline_integration.py, around line 188
    final_line_count = len(jsonl_files[0].read_text().strip().split("\n"))
    assert final_line_count == first_line_count, (
        f"--force should replace, not append: expected {first_line_count} lines, got {final_line_count}"
    )
```

## Warnings

### WR-01: Hardcoded audio path bypasses `settings.data_dir`

**File:** `bibliavox/cli/export.py:126`
**Issue:** The audio file path is computed as a hardcoded relative string `f"data/prepared/audio/{book}/{chapter_num:03d}.wav"` instead of using `settings.data_dir`. When `BIBLIAVOX_DATA_DIR` is overridden (e.g., to `/custom/data`), the `audio_file` field in the JSONL output will contain the wrong path. This is a metadata correctness issue — downstream consumers reading the JSONL will get invalid audio file references.
**Fix:**
```python
# bibliavox/cli/export.py, line 126
            audio_file = str(settings.data_dir / "prepared" / "audio" / book / f"{chapter_num:03d}.wav")
```

### WR-02: Unhandled `json.JSONDecodeError` in `export_chapter_jsonl`

**File:** `bibliavox/export/writer.py:109-110`
**Issue:** `json.load(f)` on the matched JSON file has no error handling. If the file is malformed (truncated, invalid JSON), a raw `json.JSONDecodeError` propagates up. The CLI catches it generically at line 148-150, but the error message will be the raw exception text without context about which file failed or why. Compare this to the careful error handling in `load_canonical_text` (line 54-62) which logs and skips malformed lines.
**Fix:**
```python
# bibliavox/export/writer.py, around line 109
    try:
        with open(matched_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed matched JSON at {matched_path}: {e}") from e
```

### WR-03: Missing key validation in matched JSON data

**File:** `bibliavox/export/writer.py:112-116`
**Issue:** The code accesses `data["model"]`, `data["chapter"]`, and `data["verses"]` without checking they exist. A matched JSON file missing any of these keys will produce a bare `KeyError` with no context. The `chapter.split()` on line 114 will also fail with `IndexError` if the chapter string doesn't contain a space (e.g., just `"TIT"` instead of `"TIT 1"`).
**Fix:**
```python
# bibliavox/export/writer.py, after line 111
    required_keys = ("model", "chapter", "verses")
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Matched JSON {matched_path} missing keys: {missing}")

    model = data["model"]
    chapter = data["chapter"]
    parts = chapter.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid chapter format in {matched_path}: {chapter!r}. Expected 'BOOK CHAPTER'.")
    book = parts[0]
    ch_num = int(parts[1])
```

### WR-04: `export:run` task passes unused `GOLD` variable

**File:** `Taskfile.yml:236-239`
**Issue:** The `export:run` task passes `GOLD: "true"` to `export:jsonl`, but `export:jsonl` already hardcodes `--gold` in its command (line 226). The `GOLD` variable is never referenced by `export:jsonl`, making the pass-through dead configuration that misleads readers into thinking `GOLD` is configurable at the `export:run` level.
**Fix:**
```yaml
  export:run:
    desc: Run full pipeline on gold chapters (text → audio → align → export)
    vars:
      MODEL: '{{default "microsoft/VibeVoice-ASR-HF" .MODEL}}'
    cmds:
      - task: export:jsonl
        vars:
          MODEL: "{{.MODEL}}"
          FORCE: "{{.FORCE}}"
    deps:
      - export:prepare-audio
      - export:align
```

## Info

### IN-01: Module-level mutable cache is not thread-safe

**File:** `bibliavox/export/writer.py:22`
**Issue:** `_CANONICAL_TEXT` is a module-level mutable global used as a cache. While this is fine for the current single-threaded CLI usage, it would cause race conditions if the module were ever used in a concurrent context (e.g., async pipeline or multi-threaded server). The `reset_canonical_text_cache()` function mitigates this for tests.
**Fix:** No action needed for v1 CLI usage. If concurrency is added later, consider `threading.Lock` or moving cache to a context object.

### IN-02: `normalize_confidence` with single non-zero score always returns 1.0

**File:** `bibliavox/export/writer.py:68-84`
**Issue:** The divide-by-max normalization means any single non-zero score normalizes to exactly 1.0, regardless of its absolute value. A confidence score of 0.001 and 100.0 both normalize to 1.0 when alone. This is expected behavior for the normalization scheme (documented as D-15), but worth noting that the normalized confidence loses absolute magnitude information.
**Fix:** No fix needed — this is inherent to the divide-by-max approach. Document the trade-off if consumers need absolute confidence.

---

_Reviewed: 2026-06-02T20:44:40Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
