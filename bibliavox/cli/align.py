import json

import typer
from rich.console import Console

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

    # Read SZIT text
    szit_path = settings.data_dir / "processed" / "text" / "szit.jsonl"
    if not szit_path.exists():
        console.print(f"[red]Error: Text corpus not found at {szit_path}[/red]")
        raise typer.Exit(1)

    verses = []
    with open(szit_path, "r", encoding="utf-8") as f:
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
            f"[red]Error: No verses found for {book} {chapter} in SZIT corpus[/red]"
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
