"""Export CLI subcommand group for JSONL generation.

Provides `bibliavox export jsonl` command with Rich progress bar,
gold chapter filtering, and idempotency checks.
"""

from __future__ import annotations

import re

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

from bibliavox.config import get_settings, parse_gold_chapters
from bibliavox.export.writer import (
    export_chapter_jsonl,
    is_chapter_complete,
    reset_canonical_text_cache,
)

app = typer.Typer(help="Export alignment results to JSONL format.")
console = Console()

# Pattern to extract book and chapter from matched JSON filenames
# e.g., TIT_001_microsoft_VibeVoice-ASR-HF_matched.json
_MATCHED_FILE_PATTERN = re.compile(r"^([A-Z0-9]+)_(\d+)_(.+)_matched\.json$")


@app.command("jsonl")
def jsonl_command(
    gold: bool = typer.Option(False, help="Export gold chapters only"),
    model: str = typer.Option(
        None, help="Specific model ID to export (defaults to all evaluated)"
    ),
    force: bool = typer.Option(False, help="Force re-export even if complete"),
) -> None:
    """Export alignment results to JSONL format with full metadata."""
    settings = get_settings()

    if not gold:
        console.print(
            "[red]Error: Must specify --gold (single chapter export not yet supported)[/red]"
        )
        raise typer.Exit(1)

    # Parse gold chapters from config (D-12)
    try:
        gold_chapters = parse_gold_chapters(settings.gold_chapters)
    except ValueError as e:
        console.print(f"[red]Error parsing gold chapters: {e}[/red]")
        raise typer.Exit(1)

    # Create output directory
    export_dir = settings.data_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    # Find matched JSON files
    eval_dir = settings.data_dir / "evaluation"
    if not eval_dir.exists():
        console.print(f"[red]Error: Evaluation directory not found at {eval_dir}[/red]")
        raise typer.Exit(1)

    # Build gold chapter lookup for fast filtering
    gold_set = set(gold_chapters)

    # Find all matched files
    matched_files = []
    for f in sorted(eval_dir.iterdir()):
        if not f.is_file() or not f.name.endswith("_matched.json"):
            continue

        match = _MATCHED_FILE_PATTERN.match(f.name)
        if not match:
            continue

        book = match.group(1)
        chapter_num = int(match.group(2))
        model_safe = match.group(3)

        # Filter by gold chapters
        if (book, chapter_num) not in gold_set:
            continue

        # Filter by model if specified
        if model:
            # Convert model ID to safe name for comparison
            model_safe_name = model.replace("/", "_")
            if model_safe != model_safe_name:
                continue

        matched_files.append((f, book, chapter_num, model_safe))

    if not matched_files:
        console.print(
            "[yellow]No matching evaluation files found for gold chapters[/yellow]"
        )
        raise typer.Exit(0)

    # Reset canonical text cache to ensure fresh load
    reset_canonical_text_cache()

    # Process files with Rich progress bar (D-11)
    exported = 0
    skipped = 0
    total_verses = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Exporting chapters...", total=len(matched_files))

        for matched_path, book, chapter_num, model_safe in matched_files:
            # Compute output paths
            audio_file = f"data/prepared/audio/{book}/{chapter_num:03d}.wav"
            output_file = export_dir / f"{book}_{chapter_num:03d}_{model_safe}.jsonl"

            # Check idempotency (D-13, D-14)
            if not force and is_chapter_complete(
                output_file, model_safe.replace("_", "/")
            ):
                skipped += 1
                progress.advance(task)
                continue

            # Export chapter
            try:
                count = export_chapter_jsonl(
                    matched_path,
                    audio_file,
                    "SZIT",
                    output_file,
                    settings.data_dir,
                )
                total_verses += count
                exported += 1
            except Exception as e:
                console.print(f"[red]Error exporting {book} {chapter_num}: {e}[/red]")
                raise typer.Exit(1)

            progress.advance(task)

    # Print summary
    console.print("\n[green]Export complete![/green]")
    console.print(f"  Chapters exported: {exported}")
    console.print(f"  Chapters skipped (already complete): {skipped}")
    console.print(f"  Total verses written: {total_verses}")
    console.print(f"  Output directory: {export_dir}")
