"""Tests for chapter preparation orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from bibliavox.audio.pipeline import prepare_chapter


def test_prepare_chapter_writes_wav_meta_and_index_sidecars(
    monkeypatch, tmp_path: Path
) -> None:
    raw_root = tmp_path / "raw"
    prepared_root = tmp_path / "prepared"
    input_mp3 = raw_root / "GEN" / "001.mp3"
    input_mp3.parent.mkdir(parents=True, exist_ok=True)
    input_mp3.write_bytes(b"mp3")

    output_wav = prepared_root / "GEN" / "001.wav"
    output_index = prepared_root / "GEN" / "001.index.json"

    def fake_convert(
        input_path: Path, output_path: Path, *, force: bool = False
    ) -> Path:
        assert input_path == input_mp3
        assert output_path == output_wav
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"wav")
        return output_path

    monkeypatch.setattr("bibliavox.audio.pipeline.convert_to_wav", fake_convert)
    monkeypatch.setattr(
        "bibliavox.audio.pipeline.probe_audio",
        lambda _: {
            "duration": 2.5,
            "bit_rate": 256000,
            "sample_rate": 16000,
            "channels": 1,
            "codec_name": "pcm_s16le",
        },
    )
    monkeypatch.setattr(
        "bibliavox.audio.pipeline.build_seek_index",
        lambda *_args, **_kwargs: output_index,
    )

    result = prepare_chapter(
        "GEN",
        1,
        raw_root=raw_root,
        prepared_root=prepared_root,
    )

    assert result["status"] == "prepared"
    assert output_wav.exists()
    assert (prepared_root / "GEN" / "001.meta.json").exists()
    meta_payload = json.loads((prepared_root / "GEN" / "001.meta.json").read_text())
    assert meta_payload["sample_rate"] == 16000
    assert meta_payload["book_usx"] == "GEN"
    assert meta_payload["chapter"] == 1
    assert result["index_path"] == output_index


def test_prepare_chapter_skips_when_all_sidecars_exist_without_force(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    prepared_root = tmp_path / "prepared"
    input_mp3 = raw_root / "GEN" / "001.mp3"
    input_mp3.parent.mkdir(parents=True, exist_ok=True)
    input_mp3.write_bytes(b"mp3")

    prepared_dir = prepared_root / "GEN"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    (prepared_dir / "001.wav").write_bytes(b"wav")
    (prepared_dir / "001.meta.json").write_text("{}")
    (prepared_dir / "001.index.json").write_text("{}")

    result = prepare_chapter(
        "GEN",
        1,
        raw_root=raw_root,
        prepared_root=prepared_root,
    )

    assert result["status"] == "skipped"
