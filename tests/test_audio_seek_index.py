"""Tests for sample-accurate seek index and WAV preview extraction."""

from __future__ import annotations

import json
import wave
from pathlib import Path

from bibliavox.audio.seek_index import (
    build_seek_index,
    resolve_sample_window,
    write_seek_preview,
)


def _write_test_wav(path: Path, sample_rate: int = 16_000, frames: int = 1600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = bytearray()
    for i in range(frames):
        value = (i % 200) - 100
        samples.extend(int(value).to_bytes(2, byteorder="little", signed=True))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(samples))


def test_build_seek_index_writes_required_schema(tmp_path: Path) -> None:
    wav_path = tmp_path / "data" / "prepared" / "audio" / "GEN" / "001.wav"
    _write_test_wav(wav_path, sample_rate=16_000, frames=3_200)

    index_path = build_seek_index(wav_path, book_usx="GEN", chapter=1)

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["sample_rate"] == 16_000
    assert payload["total_samples"] == 3_200
    assert payload["duration_sec"] == 0.2
    assert payload["wav_path"] == str(wav_path)
    assert payload["book_usx"] == "GEN"
    assert payload["chapter"] == 1
    assert payload["created_at"]


def test_resolve_sample_window_is_deterministic_and_clamped() -> None:
    index: dict[str, object] = {
        "sample_rate": 16_000,
        "total_samples": 32_000,
        "duration_sec": 2.0,
        "wav_path": "data/prepared/audio/GEN/001.wav",
        "book_usx": "GEN",
        "chapter": 1,
        "created_at": "2026-05-29T00:00:00Z",
    }

    start_sample, end_sample = resolve_sample_window(
        index, seconds=1.5, duration_sec=0.75
    )
    assert start_sample == 24_000
    assert end_sample == 32_000

    clamped_start, clamped_end = resolve_sample_window(
        index, seconds=-5, duration_sec=0.25
    )
    assert clamped_start == 0
    assert clamped_end == 4_000


def test_write_seek_preview_extracts_wav_by_sample_offsets(tmp_path: Path) -> None:
    source_wav = tmp_path / "source.wav"
    preview_wav = tmp_path / "preview.wav"
    _write_test_wav(source_wav, sample_rate=16_000, frames=16_000)

    written = write_seek_preview(
        source_wav,
        preview_wav,
        start_sample=4_000,
        end_sample=8_000,
    )

    assert written == preview_wav
    with wave.open(str(preview_wav), "rb") as wav:
        assert wav.getframerate() == 16_000
        assert wav.getnchannels() == 1
        assert wav.getnframes() == 4_000
