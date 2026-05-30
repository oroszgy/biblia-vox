"""Audio subcommand group for discovery, download, conversion, prepare, and seek."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
import json
import time
from threading import Lock

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from bibliavox.audio.discovery import (
    BASE_AUDIO_URL,
    build_audio_manifest,
    inventory_report,
    parse_m3u,
)
from bibliavox.audio.downloader import DownloadResult, download_all, download_chapter
from bibliavox.audio.convert import AudioConversionError, convert_to_wav
from bibliavox.audio.metadata import AudioProbeError, format_audio_info, probe_audio
from bibliavox.audio.pipeline import prepare_chapter
from bibliavox.audio.seek_index import (
    SeekIndexError,
    resolve_sample_window,
    write_seek_preview,
)

app = typer.Typer(name="audio", help="Bible audio operations")
console = Console()


def _validate_index_payload(index_payload: dict[str, Any]) -> None:
    for field in ("sample_rate", "total_samples", "duration_sec", "wav_path"):
        if field not in index_payload:
            raise SeekIndexError(
                f"Invalid seek index: missing required field '{field}'"
            )

    sample_rate = int(index_payload["sample_rate"])
    total_samples = int(index_payload["total_samples"])
    duration_sec = float(index_payload["duration_sec"])
    if sample_rate <= 0 or total_samples < 0 or duration_sec < 0:
        raise SeekIndexError(
            "Invalid seek index: sample_rate must be > 0 and total_samples/duration_sec must be non-negative"
        )


def _is_within_root(path: Path, root: Path) -> bool:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
        return True
    except ValueError:
        return False


def _validate_seek_output_path(output_path: Path, prepared_root: Path) -> Path:
    resolved_root = prepared_root.resolve()
    candidate = (
        output_path if output_path.is_absolute() else (resolved_root / output_path)
    )
    candidate = candidate.resolve()

    if output_path.is_absolute():
        allowed_roots = [resolved_root, Path("/tmp").resolve()]
    else:
        allowed_roots = [resolved_root]
    if not any(_is_within_root(candidate, root) for root in allowed_roots):
        raise SeekIndexError(
            "Output path is restricted. Use a path under prepared root "
            "or /tmp for preview output."
        )
    return candidate


def load_mek_playlist() -> str:
    """Fetch MEK M3U playlist text."""
    playlist_url = f"{BASE_AUDIO_URL}/biblia.m3u"
    attempts = 5
    timeout = httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=10.0)
    for attempt in range(1, attempts + 1):
        try:
            response = httpx.get(playlist_url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError:
            if attempt == attempts:
                raise
            time.sleep(min(2**attempt, 10))
    raise RuntimeError("unreachable")


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

        total_items = len(manifest)
        status_lock = Lock()
        counts = {"downloaded": 0, "skipped": 0, "failed": 0}

        console.print("[cyan]Batch progress enabled[/cyan]")

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TaskProgressColumn(),
            TextColumn("• {task.completed}/{task.total}"),
            TextColumn(
                "• d={task.fields[downloaded]} s={task.fields[skipped]} f={task.fields[failed]}"
            ),
            transient=True,
            console=console,
        )

        def _on_result(result: DownloadResult) -> None:
            status = str(result["status"])
            with status_lock:
                if status in counts:
                    counts[status] += 1
                progress.advance(task_id, 1)
                progress.update(
                    task_id,
                    downloaded=counts["downloaded"],
                    skipped=counts["skipped"],
                    failed=counts["failed"],
                )

        with progress:
            task_id = progress.add_task(
                "Batch progress",
                total=total_items,
                downloaded=0,
                skipped=0,
                failed=0,
            )

            summary = download_all(
                cast(list[dict[str, Any]], manifest),
                output_root,
                workers=workers,
                force=force,
                on_result=_on_result,
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
        converted = convert_to_wav(input_mp3, output_wav, force=force)
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


@app.command()
def prepare(
    book: str = typer.Option(..., "--book", "-b", help="USX book code"),
    chapter: int = typer.Option(..., "--chapter", "-c", min=1, help="Chapter number"),
    force: bool = typer.Option(
        False, "--force", help="Recreate existing prepared artifacts"
    ),
    raw_root: Path = typer.Option(
        Path("data/raw/audio"),
        "--raw-root",
        help="Raw audio root",
    ),
    prepared_root: Path = typer.Option(
        Path("data/prepared/audio"),
        "--prepared-root",
        help="Prepared audio root",
    ),
) -> None:
    """Prepare chapter WAV + metadata + seek index sidecars."""
    try:
        result = prepare_chapter(
            book.upper(),
            chapter,
            raw_root=raw_root,
            prepared_root=prepared_root,
            force=force,
        )
    except (
        AudioConversionError,
        AudioProbeError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if result["status"] == "skipped":
        console.print(
            "[yellow]Skipped existing prepared artifacts (use --force to rebuild)[/yellow]"
        )
    else:
        console.print("[green]Prepared chapter artifacts[/green]")

    console.print(f"wav={result['wav_path']}")
    console.print(f"meta={result['meta_path']}")
    console.print(f"index={result['index_path']}")


@app.command()
def seek(
    book: str = typer.Option(..., "--book", "-b", help="USX book code"),
    chapter: int = typer.Option(..., "--chapter", "-c", min=1, help="Chapter number"),
    seconds: float = typer.Option(
        ..., "--seconds", min=0.0, help="Seek start timestamp in seconds"
    ),
    duration_sec: float = typer.Option(
        2.0,
        "--duration-sec",
        min=0.0,
        help="Preview window duration in seconds",
    ),
    output: Path | None = typer.Option(
        None, "--output", help="Output preview WAV path"
    ),
    prepared_root: Path = typer.Option(
        Path("data/prepared/audio"),
        "--prepared-root",
        help="Prepared audio root",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing preview output"
    ),
) -> None:
    """Extract WAV preview window for sample-accurate timestamp verification."""
    book_usx = book.upper()
    chapter_root = prepared_root / book_usx
    index_path = chapter_root / f"{chapter:03d}.index.json"
    default_output = chapter_root / f"{chapter:03d}.seek-preview.wav"
    output_path = output or default_output

    if not index_path.exists():
        console.print(f"[red]Seek index not found: {index_path}[/red]")
        raise typer.Exit(code=1)

    if output_path.exists() and not force:
        console.print(
            f"[yellow]Skipped existing preview output (use --force to rewrite): {output_path}[/yellow]"
        )
        return

    try:
        validated_output_path = _validate_seek_output_path(output_path, prepared_root)
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SeekIndexError("Invalid seek index: expected JSON object")

        index_payload = cast(dict[str, Any], payload)
        _validate_index_payload(index_payload)
        wav_path = Path(str(index_payload["wav_path"]))
        if not _is_within_root(wav_path, prepared_root):
            raise SeekIndexError(
                "Invalid seek index: wav_path must be under prepared root"
            )
        start_sample, end_sample = resolve_sample_window(
            index_payload,
            seconds=seconds,
            duration_sec=duration_sec,
        )
        written = write_seek_preview(
            wav_path,
            validated_output_path,
            start_sample=start_sample,
            end_sample=end_sample,
        )
    except (OSError, ValueError, SeekIndexError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    # Deterministic seek report for reproducible verification.
    console.print("[green]Seek preview written[/green]")
    console.print(f"source_wav={wav_path}")
    console.print(f"start_sample={start_sample}")
    console.print(f"end_sample={end_sample}")
    console.print(f"output={written}")
