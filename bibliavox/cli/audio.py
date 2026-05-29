"""Audio subcommand group for discovery, download, conversion, and info."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import httpx
import typer
from rich.console import Console

from bibliavox.audio.discovery import (
    BASE_AUDIO_URL,
    build_audio_manifest,
    inventory_report,
    parse_m3u,
)
from bibliavox.audio.downloader import download_all, download_chapter
from bibliavox.audio.convert import AudioConversionError, convert_to_wav
from bibliavox.audio.metadata import AudioProbeError, format_audio_info, probe_audio

app = typer.Typer(name="audio", help="Bible audio operations")
console = Console()


def load_mek_playlist() -> str:
    """Fetch MEK M3U playlist text."""
    playlist_url = f"{BASE_AUDIO_URL}/biblia.m3u"
    response = httpx.get(playlist_url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


@app.command()
def download(
    book: str | None = typer.Option(None, "--book", "-b", help="USX book code"),
    chapter: int | None = typer.Option(None, "--chapter", "-c", help="Chapter number"),
    all_books: bool = typer.Option(False, "--all", "-a", help="Download all chapters"),
    workers: int = typer.Option(4, "--workers", "-w", min=1, help="Batch worker count"),
    force: bool = typer.Option(False, "--force", help="Re-download existing files"),
    output_root: Path = typer.Option(
        Path("data/raw/audio"),
        "--output-root",
        help="Raw artifact root path",
    ),
) -> None:
    """Download one chapter or all chapters from MEK manifest."""
    if all_books and (book is not None or chapter is not None):
        console.print("[red]--all cannot be combined with --book/--chapter[/red]")
        raise typer.Exit(code=1)

    if not all_books and (book is None or chapter is None):
        console.print("[red]Specify either --all or --book with --chapter[/red]")
        raise typer.Exit(code=1)

    try:
        playlist = load_mek_playlist()
    except httpx.HTTPError as exc:
        console.print(f"[red]Failed to load MEK playlist: {exc}[/red]")
        raise typer.Exit(code=1)

    manifest = build_audio_manifest(parse_m3u(playlist.splitlines()))
    if not manifest:
        console.print("[red]Playlist parsed to an empty manifest[/red]")
        raise typer.Exit(code=1)

    if all_books:
        report = inventory_report(manifest)
        missing = report["missing_vs_schema"]
        extra = report["extra_vs_schema"]
        if missing or extra:
            console.print("[yellow]Inventory discrepancy diagnostics:[/yellow]")
            if missing:
                console.print(f"  missing_vs_schema: {missing}")
            if extra:
                console.print(f"  extra_vs_schema: {extra}")

        summary = download_all(
            cast(list[dict[str, Any]], manifest),
            output_root,
            workers=workers,
            force=force,
        )
        console.print(
            "[green]Batch complete[/green] "
            f"downloaded={len(summary['downloaded'])} "
            f"skipped={len(summary['skipped'])} "
            f"failed={len(summary['failed'])}"
        )
        if summary["failed"]:
            raise typer.Exit(code=1)
        return

    book_usx = str(book).upper()
    assert chapter is not None
    selected = next(
        (
            item
            for item in manifest
            if item["book_usx"] == book_usx and item["chapter"] == chapter
        ),
        None,
    )
    if selected is None:
        console.print(
            f"[red]Chapter not found in playlist manifest: {book_usx} {chapter}[/red]"
        )
        raise typer.Exit(code=1)

    result = download_chapter(cast(dict[str, Any], selected), output_root, force=force)
    if result["status"] == "failed":
        console.print(f"[red]Download failed: {result['error']}[/red]")
        raise typer.Exit(code=1)

    if result["status"] == "skipped":
        console.print(f"[yellow]Skipped existing file: {result['target']}[/yellow]")
    else:
        console.print(f"[green]Downloaded: {result['target']}[/green]")


@app.command()
def convert(
    book: str = typer.Option(..., "--book", "-b", help="USX book code"),
    chapter: int = typer.Option(..., "--chapter", "-c", help="Chapter number"),
    force: bool = typer.Option(False, "--force", help="Re-convert existing WAV"),
) -> None:
    """Convert one raw chapter MP3 into prepared WAV."""
    book_usx = book.upper()
    input_mp3 = Path("data/raw/audio") / book_usx / f"{chapter:03d}.mp3"
    output_wav = Path("data/prepared/audio") / book_usx / f"{chapter:03d}.wav"

    if not input_mp3.exists():
        console.print(f"[red]Input MP3 not found: {input_mp3}[/red]")
        raise typer.Exit(code=1)

    if output_wav.exists() and not force:
        console.print(
            f"[yellow]Skipped existing WAV (use --force to reconvert): {output_wav}[/yellow]"
        )
        return

    try:
        converted = convert_to_wav(input_mp3, output_wav)
    except AudioConversionError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Converted: {converted}[/green]")


@app.command()
def info(
    book: str = typer.Option(..., "--book", "-b", help="USX book code"),
    chapter: int = typer.Option(..., "--chapter", "-c", help="Chapter number"),
) -> None:
    """Show deterministic metadata for raw chapter audio."""
    book_usx = book.upper()
    input_audio = Path("data/raw/audio") / book_usx / f"{chapter:03d}.mp3"

    try:
        metadata = probe_audio(input_audio)
    except AudioProbeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print(format_audio_info(input_audio, metadata))
