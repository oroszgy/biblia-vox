"""BibliaVox CLI entry point.

Registers all sub-command groups and provides the main() entry point
for the console_scripts entry in pyproject.toml.
"""

from __future__ import annotations

import typer

from bibliavox.cli.align import app as align_app
from bibliavox.cli.audio import app as audio_app
from bibliavox.cli.data import app as data_app
from bibliavox.cli.export import app as export_app
from bibliavox.cli.reference import app as reference_app
from bibliavox.cli.text import app as text_app

app = typer.Typer(
    name="bibliavox",
    help="Catholic Bible verse-to-audio alignment tool",
    no_args_is_help=True,
)
app.add_typer(reference_app, name="reference", help="Bible reference data operations")
app.add_typer(text_app, name="text", help="Bible text operations")
app.add_typer(audio_app, name="audio", help="Bible audio operations")
app.add_typer(data_app, name="data", help="Dataset coverage operations")
app.add_typer(align_app, name="align", help="Text-to-audio alignment operations")
app.add_typer(export_app, name="export", help="Export alignment results")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
