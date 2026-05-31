import json

import typer
from rich.console import Console

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
