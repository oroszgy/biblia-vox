"""Audio metadata extraction helpers via ffprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


class AudioProbeError(RuntimeError):
    """Raised when ffprobe fails or required metadata is missing."""


def _assert_ffprobe_available() -> None:
    if shutil.which("ffprobe") is None:
        raise AudioProbeError(
            "ffprobe is required for audio metadata inspection. "
            "Install ffprobe (ffmpeg package) and ensure it is available on PATH."
        )


def probe_audio(path: Path) -> dict[str, Any]:
    """Probe audio file metadata and normalize key fields."""
    _assert_ffprobe_available()

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-print_format",
        "json",
        str(path),
    ]
    process = subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if process.returncode != 0:
        raise AudioProbeError(f"ffprobe failed for {path}: {process.stderr.strip()}")

    try:
        parsed = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AudioProbeError(f"ffprobe output parse error for {path}: {exc}") from exc

    streams = parsed.get("streams") or []
    if not streams:
        raise AudioProbeError(f"ffprobe returned no streams for {path}")

    stream = streams[0]
    fmt = parsed.get("format") or {}

    try:
        return {
            "duration": float(fmt["duration"]),
            "bit_rate": int(fmt["bit_rate"]),
            "sample_rate": int(stream["sample_rate"]),
            "channels": int(stream["channels"]),
            "codec_name": str(stream["codec_name"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise AudioProbeError(
            f"ffprobe missing required fields for {path}: {exc}"
        ) from exc


def format_audio_info(path: Path, info: dict[str, Any]) -> str:
    """Return deterministic metadata text for CLI output."""
    return (
        f"path={path}\n"
        f"duration={info['duration']}\n"
        f"bit_rate={info['bit_rate']}\n"
        f"sample_rate={info['sample_rate']}\n"
        f"channels={info['channels']}\n"
        f"codec_name={info['codec_name']}"
    )
