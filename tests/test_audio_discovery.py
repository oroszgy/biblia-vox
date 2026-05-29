"""Tests for audio playlist discovery and inventory reporting."""

from __future__ import annotations

from bibliavox.audio.discovery import build_audio_manifest, inventory_report, parse_m3u


def test_parse_m3u_extracts_extinf_and_normalized_mp3_path() -> None:
    lines = [
        "#EXTM3U",
        "#EXTINF:387,Teremtes-konyve-01",
        r"otestamentum\01_teremtes\teremtes-konyve-01.mp3",
    ]

    parsed = parse_m3u(lines)

    assert parsed == [
        {
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "extinf_sec": 387,
        }
    ]


def test_build_audio_manifest_maps_playlist_entries_to_book_chapter_records() -> None:
    entries = [
        {
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "extinf_sec": 387,
        },
        {
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-02.mp3",
            "extinf_sec": 365,
        },
    ]

    manifest = build_audio_manifest(entries)

    assert manifest == [
        {
            "book_usx": "GEN",
            "chapter": 1,
            "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "extinf_sec": 387,
            "source": "mek.m3u",
        },
        {
            "book_usx": "GEN",
            "chapter": 2,
            "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-02.mp3",
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-02.mp3",
            "extinf_sec": 365,
            "source": "mek.m3u",
        },
    ]


def test_inventory_report_returns_missing_and_extra_diagnostics() -> None:
    manifest = [
        {
            "book_usx": "GEN",
            "chapter": 1,
            "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-01.mp3",
            "extinf_sec": 387,
            "source": "mek.m3u",
        },
        {
            "book_usx": "GEN",
            "chapter": 99,
            "url": "https://mek.oszk.hu/08800/08820/mp3/otestamentum/01_teremtes/teremtes-konyve-99.mp3",
            "relative_path": "otestamentum/01_teremtes/teremtes-konyve-99.mp3",
            "extinf_sec": 387,
            "source": "mek.m3u",
        },
    ]

    report = inventory_report(manifest)

    assert report["missing_vs_schema"]["GEN"][0] == 2
    assert report["extra_vs_schema"] == {"GEN": [99]}
