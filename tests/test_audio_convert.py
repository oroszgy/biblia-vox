"""Tests for ffmpeg audio conversion with strict WAV invariants."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from bibliavox.audio.convert import AudioConversionError, convert_to_wav


def test_convert_to_wav_invokes_ffmpeg_with_required_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_mp3 = tmp_path / "in.mp3"
    output_wav = tmp_path / "out.wav"
    input_mp3.write_bytes(b"fake-mp3")

    captured: dict[str, Any] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        output_wav.write_bytes(b"fake-wav")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(
        "bibliavox.audio.convert.shutil.which", lambda _: "/usr/bin/ffmpeg"
    )
    monkeypatch.setattr("bibliavox.audio.convert.subprocess.run", fake_run)
    monkeypatch.setattr(
        "bibliavox.audio.convert.probe_audio",
        lambda _: {
            "codec_name": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1,
            "duration": 1.0,
            "bit_rate": 256000,
        },
    )

    result = convert_to_wav(input_mp3, output_wav)

    assert result == output_wav
    assert captured["cmd"] == [
        "ffmpeg",
        "-y",
        "-i",
        str(input_mp3),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_wav),
    ]
    kwargs = captured["kwargs"]
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True


def test_convert_to_wav_fails_with_explicit_error_when_ffmpeg_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_mp3 = tmp_path / "in.mp3"
    output_wav = tmp_path / "out.wav"
    input_mp3.write_bytes(b"fake-mp3")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, "", "decode failed")

    monkeypatch.setattr(
        "bibliavox.audio.convert.shutil.which", lambda _: "/usr/bin/ffmpeg"
    )
    monkeypatch.setattr("bibliavox.audio.convert.subprocess.run", fake_run)

    with pytest.raises(AudioConversionError, match="ffmpeg conversion failed"):
        convert_to_wav(input_mp3, output_wav)


def test_convert_to_wav_rejects_output_when_probe_invariants_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_mp3 = tmp_path / "in.mp3"
    output_wav = tmp_path / "out.wav"
    input_mp3.write_bytes(b"fake-mp3")

    def fake_run(cmd, **kwargs):
        output_wav.write_bytes(b"fake-wav")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(
        "bibliavox.audio.convert.shutil.which", lambda _: "/usr/bin/ffmpeg"
    )
    monkeypatch.setattr("bibliavox.audio.convert.subprocess.run", fake_run)
    monkeypatch.setattr(
        "bibliavox.audio.convert.probe_audio",
        lambda _: {
            "codec_name": "pcm_s16le",
            "sample_rate": 44100,
            "channels": 1,
            "duration": 1.0,
            "bit_rate": 320000,
        },
    )

    with pytest.raises(AudioConversionError, match="invalid WAV format"):
        convert_to_wav(input_mp3, output_wav)

    assert not output_wav.exists()


def test_convert_to_wav_fails_with_setup_guidance_when_ffmpeg_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_mp3 = tmp_path / "in.mp3"
    output_wav = tmp_path / "out.wav"
    input_mp3.write_bytes(b"fake-mp3")

    monkeypatch.setattr("bibliavox.audio.convert.shutil.which", lambda _: None)

    with pytest.raises(AudioConversionError, match="Install ffmpeg"):
        convert_to_wav(input_mp3, output_wav)


def test_convert_to_wav_wraps_timeout_as_audio_conversion_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_mp3 = tmp_path / "in.mp3"
    output_wav = tmp_path / "out.wav"
    input_mp3.write_bytes(b"fake-mp3")

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=300)

    monkeypatch.setattr(
        "bibliavox.audio.convert.shutil.which", lambda _: "/usr/bin/ffmpeg"
    )
    monkeypatch.setattr("bibliavox.audio.convert.subprocess.run", fake_run)

    with pytest.raises(AudioConversionError, match="ffmpeg timed out"):
        convert_to_wav(input_mp3, output_wav)
