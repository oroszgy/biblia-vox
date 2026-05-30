"""Data coverage audit CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import typer
from rich.console import Console

from bibliavox.coverage import audit_coverage

app = typer.Typer(name="data", help="Dataset coverage operations")
console = Console()


@app.command("coverage")
def coverage(
    allow_deuterocanonical_missing: bool = typer.Option(
        False,
        "--allow-deuterocanonical-missing",
        help="Ignore missing chapters for deuterocanonical books",
    ),
    allow_known_source_gaps: bool = typer.Option(
        False,
        "--allow-known-source-gaps",
        help="Ignore gaps listed in known gaps policy file",
    ),
    fail_on_unclassified: bool = typer.Option(
        False,
        "--fail-on-unclassified",
        help="Mark audit failed if any unresolved gap has unknown classification",
    ),
    include_remote_audio: bool = typer.Option(
        True,
        "--include-remote-audio/--no-include-remote-audio",
        help="Compare local audio gaps against remote MEK manifest",
    ),
    known_gaps_path: Path = typer.Option(
        Path("data/reference/known_gaps.json"),
        "--known-gaps-path",
        help="Known source gaps policy path",
    ),
    raw_audio_root: Path = typer.Option(
        Path("data/raw/audio"),
        "--raw-audio-root",
        help="Raw audio root path",
    ),
    prepared_audio_root: Path = typer.Option(
        Path("data/prepared/audio"),
        "--prepared-audio-root",
        help="Prepared audio root path",
    ),
    raw_text_dir: Path = typer.Option(
        Path("data/raw/text"),
        "--raw-text-dir",
        help="Raw text source directory path",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print full JSON report",
    ),
) -> None:
    """Run strict text+audio dataset coverage audit."""
    report = audit_coverage(
        allow_deuterocanonical_missing=allow_deuterocanonical_missing,
        allow_known_source_gaps=allow_known_source_gaps,
        fail_on_unclassified=fail_on_unclassified,
        known_gaps_path=known_gaps_path,
        raw_audio_root=raw_audio_root,
        prepared_audio_root=prepared_audio_root,
        raw_text_dir=raw_text_dir,
        include_remote_audio=include_remote_audio,
    )

    summary = cast(dict[str, object], report["summary"])
    unresolved = cast(dict[str, int], summary["unresolved"])
    complete = bool(report["complete"])
    if json_output:
        console.print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        console.print(
            "[bold]Coverage summary[/bold] "
            f"books={summary['books_scoped']} complete={complete}"
        )
        console.print(
            "text_missing="
            f"{summary['text_missing_total']} "
            "audio_missing(raw/wav/index/meta)="
            f"{summary['audio_raw_missing_total']}/"
            f"{summary['audio_wav_missing_total']}/"
            f"{summary['audio_index_missing_total']}/"
            f"{summary['audio_meta_missing_total']}"
        )
        console.print(
            "unresolved(text/raw/wav/index/meta)="
            f"{unresolved['text_missing']}/"
            f"{unresolved['audio_raw_missing']}/"
            f"{unresolved['audio_wav_missing']}/"
            f"{unresolved['audio_index_missing']}/"
            f"{unresolved['audio_meta_missing']}"
        )
        if report.get("remote_audio_error"):
            console.print(
                f"[yellow]Remote audio inventory unavailable:[/yellow] {report['remote_audio_error']}"
            )

    if complete:
        raise typer.Exit(code=0)
    raise typer.Exit(code=1)
