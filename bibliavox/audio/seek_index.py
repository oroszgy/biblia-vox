"""Seek index and sample-accurate WAV preview helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import wave


class SeekIndexError(ValueError):
    """Raised when seek index payload or window arguments are invalid."""


def _index_path_for_wav(wav_path: Path) -> Path:
    return wav_path.with_suffix(".index.json")


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise SeekIndexError(
                f"Invalid seek index: {field_name} must be integer-like"
            ) from exc
    raise SeekIndexError(f"Invalid seek index: {field_name} has unsupported type")


def build_seek_index(
    wav_path: Path,
    *,
    book_usx: str,
    chapter: int,
    created_at: str | None = None,
) -> Path:
    """Build and persist canonical seek index sidecar for a prepared WAV file."""
    with wave.open(str(wav_path), "rb") as wav:
        sample_rate = int(wav.getframerate())
        total_samples = int(wav.getnframes())

    duration_sec = total_samples / sample_rate if sample_rate > 0 else 0.0
    payload = {
        "sample_rate": sample_rate,
        "total_samples": total_samples,
        "duration_sec": round(duration_sec, 6),
        "wav_path": str(wav_path),
        "book_usx": book_usx.upper(),
        "chapter": int(chapter),
        "created_at": created_at or _utc_now_iso(),
    }

    index_path = _index_path_for_wav(wav_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return index_path


def resolve_sample_window(
    index_payload: dict[str, object],
    *,
    seconds: float,
    duration_sec: float,
) -> tuple[int, int]:
    """Resolve a clamped [start, end) sample window from an index payload."""
    sample_rate = _as_int(index_payload.get("sample_rate", 0), "sample_rate")
    total_samples = _as_int(index_payload.get("total_samples", 0), "total_samples")

    if sample_rate <= 0:
        raise SeekIndexError("Invalid seek index: sample_rate must be positive")
    if total_samples < 0:
        raise SeekIndexError("Invalid seek index: total_samples must be non-negative")
    if duration_sec < 0:
        raise SeekIndexError("duration_sec must be non-negative")

    start_sample = int(round(seconds * sample_rate))
    window_samples = int(round(duration_sec * sample_rate))

    start_sample = max(0, min(start_sample, total_samples))
    end_sample = start_sample + window_samples
    end_sample = max(start_sample, min(end_sample, total_samples))

    return start_sample, end_sample


def write_seek_preview(
    source_wav: Path,
    output_wav: Path,
    *,
    start_sample: int,
    end_sample: int,
) -> Path:
    """Write a WAV preview by slicing source WAV using sample offsets only."""
    if start_sample < 0:
        raise SeekIndexError("start_sample must be non-negative")
    if end_sample < start_sample:
        raise SeekIndexError("end_sample must be >= start_sample")

    with wave.open(str(source_wav), "rb") as src:
        total = src.getnframes()
        start = min(start_sample, total)
        end = min(end_sample, total)
        frame_count = max(0, end - start)

        src.setpos(start)
        frames = src.readframes(frame_count)
        params = src.getparams()

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav), "wb") as out:
        out.setparams(params)
        out.writeframes(frames)

    return output_wav
