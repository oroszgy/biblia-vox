"""Tests for audio CLI download command routing and guards."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from bibliavox.cli.audio import app

runner = CliRunner()


def test_download_requires_single_or_all_mode() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Specify either --all or --book with --chapter" in result.output


def test_download_rejects_mixed_single_and_all_mode() -> None:
    result = runner.invoke(
        app,
        ["--all", "--book", "GEN", "--chapter", "1"],
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
        ["--book", "GEN", "--chapter", "1", "--output-root", str(tmp_path)],
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

    def fake_download_all(manifest, output_root, workers=4, force=False):
        captured["manifest"] = manifest
        captured["output_root"] = output_root
        captured["workers"] = workers
        captured["force"] = force
        return {"downloaded": [], "skipped": [], "failed": []}

    monkeypatch.setattr("bibliavox.cli.audio.download_all", fake_download_all)

    result = runner.invoke(
        app,
        [
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
