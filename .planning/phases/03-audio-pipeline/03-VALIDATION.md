---
phase: 3
slug: audio-pipeline
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-29
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (pytest defaults from project root) |
| **Quick run command** | `uv run pytest tests/test_audio_discovery.py tests/test_audio_downloader.py tests/test_audio_convert.py tests/test_audio_metadata.py tests/test_audio_seek_index.py tests/test_audio_pipeline.py tests/test_audio_cli.py -x -v` |
| **Full suite command** | `uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_audio_discovery.py tests/test_audio_downloader.py tests/test_audio_convert.py tests/test_audio_metadata.py tests/test_audio_seek_index.py tests/test_audio_pipeline.py tests/test_audio_cli.py -x -v`
- **After every plan wave:** Run `uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-task Verification Map

| task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | AUD-01 | T-03-01 | Manifest parser rejects path traversal patterns and non-MP3 lines | unit | `uv run pytest tests/test_audio_discovery.py::test_parse_m3u_rejects_non_mp3 -x -v` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | AUD-01, AUD-02 | T-03-02 | Downloader enforces resume safety and worker limits | integration | `uv run pytest tests/test_audio_downloader.py -x -v` | ✅ | ⬜ pending |
| 03-01-03 | 01 | 1 | AUD-01, AUD-02 | T-03-03 | CLI enforces valid argument combinations and stable status output | unit | `uv run pytest tests/test_audio_cli.py -x -v` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | AUD-03 | T-03-05, T-03-07 | Conversion output must be `pcm_s16le`, `16000`, mono | integration | `uv run pytest tests/test_audio_convert.py -x -v` | ✅ | ⬜ pending |
| 03-02-02 | 02 | 2 | AUD-04 | T-03-08 | Metadata extraction surfaces deterministic fields and clear failures | unit | `uv run pytest tests/test_audio_metadata.py -x -v` | ✅ | ⬜ pending |
| 03-02-03 | 02 | 2 | AUD-03, AUD-04 | T-03-06 | CLI conversion/info commands fail fast on subprocess errors | integration | `uv run bibliavox audio convert --help && uv run bibliavox audio info --help` | ✅ | ⬜ pending |
| 03-03-01 | 03 | 3 | AUD-05 | T-03-09 | Seek index encodes sample-rate and total-samples integrity fields | unit | `uv run pytest tests/test_audio_seek_index.py -x -v` | ✅ | ⬜ pending |
| 03-03-02 | 03 | 3 | AUD-05 | T-03-10, T-03-11 | Pipeline preserves deterministic discover->download->convert->index ordering and status | integration | `uv run pytest tests/test_audio_pipeline.py -x -v` | ✅ | ⬜ pending |
| 03-03-03 | 03 | 3 | AUD-05 | T-03-12 | CLI seek/prepare commands constrain reads/writes to project audio roots | integration | `uv run bibliavox audio prepare --help && uv run bibliavox audio seek --help` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_audio_discovery.py` — manifest parsing and discrepancy stubs
- [x] `tests/test_audio_downloader.py` — retry/resume and range handling stubs
- [x] `tests/test_audio_convert.py` — conversion invariant stubs
- [x] `tests/test_audio_metadata.py` — ffprobe parsing and CLI rendering stubs
- [x] `tests/test_audio_seek_index.py` — sample-offset math stubs
- [x] `tests/test_audio_pipeline.py` — orchestration contract stubs
- [x] `tests/test_audio_cli.py` — command flag/dispatch stubs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Download from live MEK source with network variability | AUD-01, AUD-02 | CI and local unit tests mock HTTP responses; source uptime and remote behavior must be checked live | Run `task audio:download --book GEN --chapter 1` then `task audio:download --all --workers 4`; verify success/skip/fail totals and resulting MP3 files under `data/raw/audio/` |
| Audible spot-check at timestamp boundary | AUD-05 | Sample math can pass while content check still needs human ears | Run `uv run bibliavox audio seek --book GEN --chapter 1 --seconds 120 --duration-sec 2 --output /tmp/gen1_120s.wav` and listen for expected narration continuity |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-29
