"""MP3 to WAV conversion helpers with strict output invariants."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

REQUIRED_CODEC = "pcm_s16le"
REQUIRED_SAMPLE_RATE = 16000
REQUIRED_CHANNELS = 1
CONVERSION_TIMEOUT_SECONDS = 300


class AudioConversionError(RuntimeError):
    """Raised when conversion fails or converted output is invalid."""


def probe_audio(path: Path) -> dict[str, Any]:
    """Proxy to metadata probe implementation for testability."""
    from bibliavox.audio.metadata import probe_audio as metadata_probe_audio

    return metadata_probe_audio(path)


def _assert_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise AudioConversionError(
            "ffmpeg is required for audio conversion. "
            "Install ffmpeg and ensure it is available on PATH."
        )


def convert_to_wav(input_mp3: Path, output_wav: Path, *, force: bool = False) -> Path:
    """Convert MP3 to 16kHz mono PCM WAV and verify invariants."""
    _assert_ffmpeg_available()

    if output_wav.exists() and not force:
        return output_wav

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_mp3),
        "-ac",
        str(REQUIRED_CHANNELS),
        "-ar",
        str(REQUIRED_SAMPLE_RATE),
        "-c:a",
        REQUIRED_CODEC,
        str(output_wav),
    ]

    process = subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=CONVERSION_TIMEOUT_SECONDS,
    )

    if process.returncode != 0:
        raise AudioConversionError(
            "ffmpeg conversion failed "
            f"for {input_mp3} -> {output_wav}: {process.stderr.strip()}"
        )

    metadata = probe_audio(output_wav)
    codec_name = metadata.get("codec_name")
    sample_rate = int(metadata.get("sample_rate", 0))
    channels = int(metadata.get("channels", 0))

    if (
        codec_name != REQUIRED_CODEC
        or sample_rate != REQUIRED_SAMPLE_RATE
        or channels != REQUIRED_CHANNELS
    ):
        if output_wav.exists():
            output_wav.unlink()
        raise AudioConversionError(
            "invalid WAV format after conversion: "
            f"codec={codec_name}, sample_rate={sample_rate}, channels={channels}; "
            f"required codec={REQUIRED_CODEC}, sample_rate={REQUIRED_SAMPLE_RATE}, "
            f"channels={REQUIRED_CHANNELS}."
        )

    return output_wav
