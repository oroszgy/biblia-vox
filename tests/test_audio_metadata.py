"""Tests for ffprobe metadata extraction and audio info CLI rendering."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bibliavox.cli.audio import app
from bibliavox.audio.metadata import AudioProbeError, probe_audio

runner = CliRunner()


def test_probe_audio_returns_normalized_required_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_wav = tmp_path / "001.wav"
    input_wav.write_bytes(b"fake")

    ffprobe_json = (
        '{"streams":[{"codec_name":"pcm_s16le","sample_rate":"16000",'
        '"channels":1}],"format":{"duration":"12.345","bit_rate":"256000"}}'
    )

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, ffprobe_json, "")

    monkeypatch.setattr(
        "bibliavox.audio.metadata.shutil.which", lambda _: "/usr/bin/ffprobe"
    )
    monkeypatch.setattr("bibliavox.audio.metadata.subprocess.run", fake_run)

    info = probe_audio(input_wav)

    assert info == {
        "duration": 12.345,
        "bit_rate": 256000,
        "sample_rate": 16000,
        "channels": 1,
        "codec_name": "pcm_s16le",
    }


def test_audio_info_command_renders_metadata_for_chapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bibliavox.cli.audio.probe_audio",
        lambda path: {
            "duration": 8.5,
            "bit_rate": 256000,
            "sample_rate": 16000,
            "channels": 1,
            "codec_name": "pcm_s16le",
        },
    )

    result = runner.invoke(app, ["info", "--book", "GEN", "--chapter", "1"])

    assert result.exit_code == 0
    assert "data/raw/audio/GEN/001.mp3" in result.output
    assert "duration" in result.output
    assert "sample_rate" in result.output
    assert "codec_name" in result.output


def test_audio_info_ffprobe_failure_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_probe(_path: Path):
        raise AudioProbeError("ffprobe failed: bad media")

    monkeypatch.setattr("bibliavox.cli.audio.probe_audio", fake_probe)

    result = runner.invoke(app, ["info", "--book", "GEN", "--chapter", "1"])

    assert result.exit_code == 1
    assert "ffprobe failed" in result.output


def test_probe_audio_fails_with_setup_guidance_when_ffprobe_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_wav = tmp_path / "001.wav"
    input_wav.write_bytes(b"fake")

    monkeypatch.setattr("bibliavox.audio.metadata.shutil.which", lambda _: None)

    with pytest.raises(AudioProbeError, match="Install ffprobe"):
        probe_audio(input_wav)
