"""Tests for audio CLI download command routing and guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from bibliavox.cli.audio import app

runner = CliRunner()


def test_download_requires_single_or_all_mode() -> None:
    result = runner.invoke(app, ["download"])
    assert result.exit_code == 1
    assert "Specify either --all or --book with --chapter" in result.output


def test_download_rejects_mixed_single_and_all_mode() -> None:
    result = runner.invoke(
        app,
        ["download", "--all", "--book", "GEN", "--chapter", "1"],
    )
    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_download_single_dispatches_to_download_chapter(
    monkeypatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    def fake_download_chapter(item, output_root, client=None, force=False):
        calls["item"] = item
        calls["output_root"] = output_root
        calls["force"] = force
        return {
            "book_usx": item["book_usx"],
            "chapter": item["chapter"],
            "target": "dummy",
            "status": "downloaded",
            "error": None,
        }

    monkeypatch.setattr("bibliavox.cli.audio.download_chapter", fake_download_chapter)
    monkeypatch.setattr("bibliavox.cli.audio.load_mek_playlist", lambda: "")
    monkeypatch.setattr(
        "bibliavox.cli.audio.parse_m3u",
        lambda _: [
            {
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.build_audio_manifest",
        lambda _: [
            {
                "book_usx": "GEN",
                "chapter": 1,
                "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
                "source": "mek.m3u",
            }
        ],
    )

    result = runner.invoke(
        app,
        [
            "download",
            "--book",
            "GEN",
            "--chapter",
            "1",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    item = cast(dict[str, Any], calls["item"])
    assert item["book_usx"] == "GEN"
    assert item["chapter"] == 1
    assert calls["output_root"] == tmp_path
    assert calls["force"] is False


def test_download_all_dispatches_to_batch(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("bibliavox.cli.audio.load_mek_playlist", lambda: "")
    monkeypatch.setattr(
        "bibliavox.cli.audio.parse_m3u",
        lambda _: [
            {
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.build_audio_manifest",
        lambda _: [
            {
                "book_usx": "GEN",
                "chapter": 1,
                "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
                "source": "mek.m3u",
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.inventory_report",
        lambda _: {"missing_vs_schema": {}, "extra_vs_schema": {}},
    )

    def fake_download_all(
        manifest, output_root, workers=4, force=False, on_result=None
    ):
        captured["manifest"] = manifest
        captured["output_root"] = output_root
        captured["workers"] = workers
        captured["force"] = force
        captured["on_result"] = on_result
        return {"downloaded": [], "skipped": [], "failed": []}

    monkeypatch.setattr("bibliavox.cli.audio.download_all", fake_download_all)

    result = runner.invoke(
        app,
        [
            "download",
            "--all",
            "--workers",
            "3",
            "--force",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert captured["workers"] == 3
    assert captured["force"] is True
    assert captured["output_root"] == tmp_path
    assert callable(captured["on_result"])


def test_download_all_shows_progress_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("bibliavox.cli.audio.load_mek_playlist", lambda: "")
    monkeypatch.setattr(
        "bibliavox.cli.audio.parse_m3u",
        lambda _: [
            {
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.build_audio_manifest",
        lambda _: [
            {
                "book_usx": "GEN",
                "chapter": 1,
                "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
                "source": "mek.m3u",
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.inventory_report",
        lambda _: {"missing_vs_schema": {}, "extra_vs_schema": {}},
    )

    def fake_download_all(
        manifest, output_root, workers=4, force=False, on_result=None
    ):
        assert callable(on_result)
        on_result(
            {
                "book_usx": "GEN",
                "chapter": 1,
                "target": str(output_root / "GEN" / "001.mp3"),
                "status": "downloaded",
                "error": None,
            }
        )
        return {
            "downloaded": [
                {
                    "book_usx": "GEN",
                    "chapter": 1,
                    "target": str(output_root / "GEN" / "001.mp3"),
                    "status": "downloaded",
                    "error": None,
                }
            ],
            "skipped": [],
            "failed": [],
        }

    monkeypatch.setattr("bibliavox.cli.audio.download_all", fake_download_all)

    result = runner.invoke(
        app,
        [
            "download",
            "--all",
            "--workers",
            "3",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Batch progress" in result.output
    assert "Batch complete" in result.output
    assert "downloaded=1 skipped=0 failed=0" in result.output


def test_download_all_exits_non_zero_when_failures_exist(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("bibliavox.cli.audio.load_mek_playlist", lambda: "")
    monkeypatch.setattr(
        "bibliavox.cli.audio.parse_m3u",
        lambda _: [
            {
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.build_audio_manifest",
        lambda _: [
            {
                "book_usx": "GEN",
                "chapter": 1,
                "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
                "extinf_sec": 387,
                "source": "mek.m3u",
            }
        ],
    )
    monkeypatch.setattr(
        "bibliavox.cli.audio.inventory_report",
        lambda _: {"missing_vs_schema": {}, "extra_vs_schema": {}},
    )

    def fake_download_all(
        manifest, output_root, workers=4, force=False, on_result=None
    ):
        assert callable(on_result)
        on_result(
            {
                "book_usx": "GEN",
                "chapter": 1,
                "target": str(output_root / "GEN" / "001.mp3"),
                "status": "failed",
                "error": "boom",
            }
        )
        return {
            "downloaded": [],
            "skipped": [],
            "failed": [
                {
                    "book_usx": "GEN",
                    "chapter": 1,
                    "target": str(output_root / "GEN" / "001.mp3"),
                    "status": "failed",
                    "error": "boom",
                }
            ],
        }

    monkeypatch.setattr("bibliavox.cli.audio.download_all", fake_download_all)

    result = runner.invoke(
        app,
        [
            "download",
            "--all",
            "--workers",
            "3",
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Batch complete" in result.output
    assert "downloaded=0 skipped=0 failed=1" in result.output


def test_prepare_command_defaults_to_skip_and_supports_force(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_prepare(
        book_usx: str,
        chapter: int,
        *,
        raw_root: Path,
        prepared_root: Path,
        force: bool = False,
    ):
        captured["book_usx"] = book_usx
        captured["chapter"] = chapter
        captured["raw_root"] = raw_root
        captured["prepared_root"] = prepared_root
        captured["force"] = force
        return {
            "status": "prepared",
            "wav_path": prepared_root / book_usx / f"{chapter:03d}.wav",
            "meta_path": prepared_root / book_usx / f"{chapter:03d}.meta.json",
            "index_path": prepared_root / book_usx / f"{chapter:03d}.index.json",
        }

    monkeypatch.setattr("bibliavox.cli.audio.prepare_chapter", fake_prepare)

    result = runner.invoke(app, ["prepare", "--book", "GEN", "--chapter", "1"])
    assert result.exit_code == 0
    assert captured["book_usx"] == "GEN"
    assert captured["chapter"] == 1
    assert captured["force"] is False

    result_force = runner.invoke(
        app,
        ["prepare", "--book", "GEN", "--chapter", "1", "--force"],
    )
    assert result_force.exit_code == 0
    assert captured["force"] is True


def test_seek_command_uses_index_and_wav_preview_primitives(
    monkeypatch, tmp_path: Path
) -> None:
    prepared_root = tmp_path / "prepared"
    index_path = prepared_root / "GEN" / "001.index.json"
    wav_path = prepared_root / "GEN" / "001.wav"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"wav")
    index_path.write_text(
        '{"sample_rate":16000,"total_samples":32000,"duration_sec":2.0,'
        '"wav_path":"' + str(wav_path) + '","book_usx":"GEN","chapter":1,'
        '"created_at":"2026-05-29T00:00:00Z"}'
    )

    captured: dict[str, object] = {}

    def fake_resolve(index_payload, *, seconds: float, duration_sec: float):
        captured["seconds"] = seconds
        captured["duration_sec"] = duration_sec
        captured["index_payload"] = index_payload
        return (1600, 3200)

    def fake_write_preview(
        source_wav: Path,
        output_wav: Path,
        *,
        start_sample: int,
        end_sample: int,
    ) -> Path:
        captured["source_wav"] = source_wav
        captured["output_wav"] = output_wav
        captured["start_sample"] = start_sample
        captured["end_sample"] = end_sample
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        output_wav.write_bytes(b"preview")
        return output_wav

    monkeypatch.setattr("bibliavox.cli.audio.resolve_sample_window", fake_resolve)
    monkeypatch.setattr("bibliavox.cli.audio.write_seek_preview", fake_write_preview)

    output = tmp_path / "preview.wav"
    result = runner.invoke(
        app,
        [
            "seek",
            "--book",
            "GEN",
            "--chapter",
            "1",
            "--seconds",
            "0.1",
            "--duration-sec",
            "0.1",
            "--output",
            str(output),
            "--prepared-root",
            str(prepared_root),
        ],
    )

    assert result.exit_code == 0
    assert captured["source_wav"] == wav_path
    assert captured["start_sample"] == 1600
    assert captured["end_sample"] == 3200
    assert output.exists()


def test_seek_rejects_disallowed_absolute_output_path(tmp_path: Path) -> None:
    prepared_root = tmp_path / "prepared"
    index_path = prepared_root / "GEN" / "001.index.json"
    wav_path = prepared_root / "GEN" / "001.wav"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path.write_bytes(b"wav")
    index_path.write_text(
        '{"sample_rate":16000,"total_samples":32000,"duration_sec":2.0,'
        '"wav_path":"' + str(wav_path) + '","book_usx":"GEN","chapter":1,'
        '"created_at":"2026-05-29T00:00:00Z"}'
    )

    result = runner.invoke(
        app,
        [
            "seek",
            "--book",
            "GEN",
            "--chapter",
            "1",
            "--seconds",
            "0.1",
            "--duration-sec",
            "0.1",
            "--output",
            "/etc/preview.wav",
            "--prepared-root",
            str(prepared_root),
        ],
    )

    assert result.exit_code == 1
    assert "Absolute output path is restricted" in result.output
