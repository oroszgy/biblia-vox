import json
import time
import statistics

import typer
from rich.console import Console
from rich.table import Table

from bibliavox.align.match import match_verses
from bibliavox.align.transcribe import transcribe_audio
from bibliavox.config import get_settings

app = typer.Typer(help="Alignment commands for text to audio synchronization.")
console = Console()


@app.command("transcribe")
def transcribe_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    model: str = typer.Option(
        None, help="Specific model ID to run (defaults to all in gauntlet)"
    ),
) -> None:
    """Transcribe audio and generate word-level timestamps."""
    settings = get_settings()

    audio_path = settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
    if not audio_path.exists():
        console.print(f"[red]Error: Audio file not found at {audio_path}[/red]")
        raise typer.Exit(1)

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]
        if not models_to_run:
            console.print(
                f"[red]Error: Model {model} not found in gauntlet configuration[/red]"
            )
            raise typer.Exit(1)

    align_dir = settings.data_dir / "processed" / "align"
    align_dir.mkdir(parents=True, exist_ok=True)

    for model_config in models_to_run:
        console.print(f"[cyan]Transcribing with {model_config.id}...[/cyan]")
        try:
            words = transcribe_audio(audio_path, model_config, settings.models_dir)

            # Sanitize model name for filesystem
            model_safe_name = model_config.id.replace("/", "_")
            out_path = (
                align_dir / f"{book}_{chapter:03d}_{model_safe_name}_transcript.json"
            )

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(words, f, ensure_ascii=False, indent=2)

            console.print(f"[green]Saved {len(words)} words to {out_path}[/green]")
        except Exception as e:
            console.print(f"[red]Transcription failed for {model_config.id}: {e}[/red]")
            raise typer.Exit(1)


@app.command("match")
def match_command(
    book: str = typer.Option(..., help="USX book code (e.g. GEN)"),
    chapter: int = typer.Option(..., help="Chapter number"),
    model: str = typer.Option(
        None, help="Specific model ID to match (defaults to all in gauntlet)"
    ),
) -> None:
    """Match transcribed words to Bible verse canonical text."""
    settings = get_settings()

    # Read MEK text (primary canonical source)
    mek_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not mek_path.exists():
        console.print(f"[red]Error: Text corpus not found at {mek_path}[/red]")
        raise typer.Exit(1)

    verses = []
    with open(mek_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            if verse.get("book") == book and verse.get("chapter") == chapter:
                verses.append(
                    {"verse_id": str(verse.get("verse")), "text": verse.get("text", "")}
                )

    if not verses:
        console.print(
            f"[red]Error: No verses found for {book} {chapter} in MEK corpus[/red]"
        )
        raise typer.Exit(1)

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]

    align_dir = settings.data_dir / "processed" / "align"

    for model_config in models_to_run:
        model_safe_name = model_config.id.replace("/", "_")
        transcript_path = (
            align_dir / f"{book}_{chapter:03d}_{model_safe_name}_transcript.json"
        )

        if not transcript_path.exists():
            console.print(
                f"[yellow]Skipping {model_config.id}: transcript not found[/yellow]"
            )
            continue

        with open(transcript_path, "r", encoding="utf-8") as f:
            word_transcripts = json.load(f)

        console.print(f"[cyan]Matching verses for {model_config.id}...[/cyan]")
        matched_verses = match_verses(verses, word_transcripts)

        out_path = align_dir / f"{book}_{chapter:03d}_{model_safe_name}_verses.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(matched_verses, f, ensure_ascii=False, indent=2)

        console.print(
            f"[green]Saved {len(matched_verses)} matched verses to {out_path}[/green]"
        )


@app.command("evaluate-gold")
def evaluate_gold_command(
    model: str = typer.Option(
        None, help="Specific model ID to run (defaults to all in gauntlet)"
    ),
) -> None:
    """Run transcription, alignment, and metrics calculation on 10 gold chapters."""
    settings = get_settings()

    # Define the 10 representative gold chapters
    GOLD_CHAPTERS = [
        ("TIT", 1),
        ("TIT", 2),
        ("TIT", 3),
        ("ZEP", 1),
        ("ZEP", 2),
        ("ZEP", 3),
        ("TOB", 1),
        ("TOB", 2),
        ("TOB", 3),
        ("TOB", 4),
    ]

    # Load canonical verses from MEK (primary source: all 73 books)
    text_path = settings.data_dir / "processed" / "text" / "mek.jsonl"
    if not text_path.exists():
        console.print(f"[red]Error: Text corpus not found at {text_path}[/red]")
        raise typer.Exit(1)

    all_verses = []
    with open(text_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            verse = json.loads(line)
            all_verses.append(
                {
                    "book": verse.get("book", ""),
                    "chapter": int(verse.get("chapter", 0)),
                    "verse_id": str(verse.get("verse", "")),
                    "text": verse.get("text", ""),
                }
            )

    models_to_run = settings.gauntlet.models
    if model:
        models_to_run = [m for m in models_to_run if m.id == model]
        if not models_to_run:
            console.print(
                f"[red]Error: Model {model} not found in gauntlet configuration[/red]"
            )
            raise typer.Exit(1)

    eval_dir = settings.data_dir / "processed" / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {}

    for model_config in models_to_run:
        console.print(f"[cyan]Evaluating model: {model_config.id}[/cyan]")
        model_safe_name = model_config.id.replace("/", "_")

        table = Table(title=f"Gold Evaluation Metrics: {model_config.id}")
        table.add_column("Chapter", justify="left")
        table.add_column("Canonical Verses", justify="right")
        table.add_column("Aligned Verses", justify="right")
        table.add_column("Coverage (%)", justify="right")
        table.add_column("Avg Conf", justify="right")
        table.add_column("Median Conf", justify="right")
        table.add_column("Chrono Violations", justify="right")
        table.add_column("Time (s)", justify="right")

        model_results = []
        total_canonical = 0
        total_aligned = 0
        all_confidences = []
        total_violations = 0
        total_time = 0.0

        for book, chapter in GOLD_CHAPTERS:
            chapter_verses = [
                v for v in all_verses if v["book"] == book and v["chapter"] == chapter
            ]
            if not chapter_verses:
                console.print(
                    f"[yellow]Skipping {book} {chapter}: no canonical text verses[/yellow]"
                )
                continue

            audio_path = (
                settings.data_dir / "prepared" / "audio" / book / f"{chapter:03d}.wav"
            )
            if not audio_path.exists():
                console.print(
                    f"[yellow]Skipping {book} {chapter}: WAV audio file not found[/yellow]"
                )
                continue

            console.print(f"  Processing {book} Chapter {chapter}...")
            start_time = time.perf_counter()

            try:
                words = transcribe_audio(audio_path, model_config, settings.models_dir)
                matched = match_verses(chapter_verses, words)
            except Exception as e:
                console.print(f"[red]  Failed to process {book} {chapter}: {e}[/red]")
                continue

            elapsed = time.perf_counter() - start_time

            # Compute metrics
            num_canonical = len(chapter_verses)
            num_aligned = len(matched)
            coverage = (
                (num_aligned / num_canonical * 100.0) if num_canonical > 0 else 0.0
            )

            confidences = [
                m["confidence_score"] for m in matched if "confidence_score" in m
            ]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            med_conf = statistics.median(confidences) if confidences else 0.0

            violations = 0
            prev_start = None
            for m in matched:
                s_sec = m["start_sec"]
                if prev_start is not None and s_sec < prev_start:
                    violations += 1
                prev_start = s_sec

            # Save matched verses to filesystem
            out_path = eval_dir / f"{book}_{chapter:03d}_{model_safe_name}_matched.json"
            with open(out_path, "w", encoding="utf-8") as out_f:
                json.dump(matched, out_f, ensure_ascii=False, indent=2)

            table.add_row(
                f"{book} {chapter}",
                str(num_canonical),
                str(num_aligned),
                f"{coverage:.1f}%",
                f"{avg_conf:.1f}",
                f"{med_conf:.1f}",
                str(violations),
                f"{elapsed:.1f}",
            )

            # Update aggregates
            total_canonical += num_canonical
            total_aligned += num_aligned
            all_confidences.extend(confidences)
            total_violations += violations
            total_time += elapsed

            model_results.append(
                {
                    "book": book,
                    "chapter": chapter,
                    "canonical_verses": num_canonical,
                    "aligned_verses": num_aligned,
                    "coverage_pct": coverage,
                    "avg_confidence": avg_conf,
                    "median_confidence": med_conf,
                    "chronological_violations": violations,
                    "time_sec": elapsed,
                    "output_file": str(out_path),
                }
            )

        # Calculate final overall aggregates
        overall_coverage = (
            (total_aligned / total_canonical * 100.0) if total_canonical > 0 else 0.0
        )
        overall_avg_conf = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )
        overall_med_conf = (
            statistics.median(all_confidences) if all_confidences else 0.0
        )

        table.add_section()
        table.add_row(
            "Overall / Total",
            str(total_canonical),
            str(total_aligned),
            f"{overall_coverage:.1f}%",
            f"{overall_avg_conf:.1f}",
            f"{overall_med_conf:.1f}",
            str(total_violations),
            f"{total_time:.1f}",
            style="bold",
        )

        console.print(table)

        summary_data[model_config.id] = {
            "total_canonical": total_canonical,
            "total_aligned": total_aligned,
            "overall_coverage_pct": overall_coverage,
            "overall_avg_confidence": overall_avg_conf,
            "overall_median_confidence": overall_med_conf,
            "total_chronological_violations": total_violations,
            "total_time_sec": total_time,
            "chapters": model_results,
        }

    # Save summary report to JSON
    summary_path = eval_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump(summary_data, sf, ensure_ascii=False, indent=2)

    console.print(
        f"[green]Successfully saved master evaluation summary to {summary_path}[/green]"
    )


@app.command("setup")
def setup_command() -> None:
    """Pre-download model weights specified in the gauntlet configuration."""
    from huggingface_hub import snapshot_download  # type: ignore[import-untyped]

    settings = get_settings()
    models_dir = settings.models_dir

    for model in settings.gauntlet.models:
        console.print(f"[cyan]Downloading {model.id}...[/cyan]")
        local_dir = models_dir / model.id
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            snapshot_download(
                repo_id=model.id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
            )
            console.print(f"[green]Successfully downloaded {model.id}[/green]")
        except Exception as exc:
            console.print(f"[red]Failed to download {model.id}: {exc}[/red]")
            raise typer.Exit(1)
