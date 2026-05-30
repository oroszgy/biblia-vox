# SECURITY — Phase 2.5 (2.5-data-quality)

## Scope audited
- JSON parsing/loading: `bibliavox/text/source.py`
- JSONL conversion: `bibliavox/text/jsonl_converter.py`
- Verse splitting/JSONL re-write: `bibliavox/text/splitter.py`
- CLI entrypoints for conversion/fixing: `bibliavox/cli/text.py`
- Validation logic: `bibliavox/text/validator.py`
- Pipeline invocation: `Taskfile.yml`

## Trust boundaries
1. **External content boundary**: downloaded `data/raw/text/H_Kaldi_SZIT.json` (network-origin file) enters parser (`load_szit_json`).
2. **CLI boundary**: user-supplied `--input/--output` filesystem paths enter write/read operations.
3. **Local artifact boundary**: generated `szit.jsonl` / `szit-fixed.jsonl` become downstream inputs; corruption here propagates.

## Threat Register (practical, implementation-grounded)

| Threat ID | Category | Component | Disposition | Status | Evidence |
|---|---|---|---|---|---|
| T25-DQ-01 | Unsafe parsing / code execution | `load_szit_json` | mitigate | CLOSED | Parser uses `ast.literal_eval` fallback to `json.loads`, no `eval/exec` (`bibliavox/text/source.py:49-55`). |
| T25-DQ-02 | Unauthorized schema/book injection into JSONL output | `convert_to_jsonl` | mitigate | CLOSED | Unknown books are explicitly skipped via mapping gate (`mapping.get(...); if not usx_code: continue`) (`bibliavox/text/jsonl_converter.py:44-46`). |
| T25-DQ-03 | Text integrity drift from Unicode/whitespace forms | converter normalization | mitigate | CLOSED | Each verse text is normalized before write (`normalize_text(text)`) (`bibliavox/text/jsonl_converter.py:55`), with NFC + whitespace normalization (`bibliavox/text/normalizer.py:35-47`). |
| T25-DQ-04 | Arbitrary path write / clobber via CLI-controlled output path | `text convert-jsonl`, `text fix-verses` | mitigate | OPEN | No path allowlist/repo-root confinement checks before `open(..., "w")`; CLI accepts arbitrary `Path` (`bibliavox/cli/text.py:331-359`, `bibliavox/text/jsonl_converter.py:42`, `bibliavox/text/splitter.py:182`). |
| T25-DQ-05 | Partial/corrupt artifact on interruption (non-atomic writes) | JSONL writers | mitigate | OPEN | Direct writes to target file with `open(..., "w")`; no temp-file + atomic rename pattern observed (`bibliavox/text/jsonl_converter.py:42-58`, `bibliavox/text/splitter.py:182-184`). |
| T25-DQ-06 | Malformed JSONL line causes hard-fail (availability) | `fix_verses` reader | mitigate | OPEN | Per-line `json.loads(line)` has no guarded handling/recovery; one bad line aborts run (`bibliavox/text/splitter.py:99-103`). |
| T25-DQ-07 | Silent data-quality regressions in verse/chapter consistency | validation engine | mitigate | CLOSED | Explicit checks for missing schema entities + verse count mismatch + empty verse text (`bibliavox/text/validator.py:72-123`). |

## Threat Flags (from summaries)
- No `## Threat Flags` section was found in:
  - `.planning/phases/2.5-data-quality/02.5-01-SUMMARY.md`
  - `.planning/phases/2.5-data-quality/02.5-02-SUMMARY.md`
  - `.planning/phases/2.5-data-quality/02.5-03-SUMMARY.md`
- Therefore, no unregistered threat flags could be mapped or promoted.

## Accepted risks log (current)
- None documented yet.

## Audit result
- threats_total: **7**
- threats_closed: **4**
- threats_open: **3**

Phase 2.5 is **not secure-to-ship as-is** under a mitigation-required stance due to open filesystem-write and resilience controls.
