"""Text subcommand group for Bible text operations.

Commands:
    fetch   — Fetch and display Bible text by book/chapter
    info    — Show book info including chapter/verse counts
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from bibliavox.reference.books import lookup_by_abbreviation, lookup_by_usx_code
from bibliavox.reference.schema import get_versification, load_versification
from bibliavox.text.mapping import english_to_usx, load_book_mapping
from bibliavox.text.source import get_chapter_verses, load_szit_json

app = typer.Typer(name="text", help="Bible text operations")
console = Console()


def _resolve_book(book_id: str):
    """Resolve book ID (USX code or abbreviation) to Book object."""
    book = lookup_by_usx_code(book_id)
    if book is None:
        book = lookup_by_abbreviation(book_id)
    if book is None:
        console.print(f"[red]Unknown book: {book_id}[/red]")
        raise typer.Exit(code=1)
    return book


@app.command()
def fetch(
    book: str = typer.Option(
        ..., "--book", "-b", help="USX code or Hungarian abbreviation"
    ),
    chapter: int | None = typer.Option(
        None, "--chapter", "-c", help="Chapter number (omit for all)"
    ),
) -> None:
    """Fetch and display Bible text."""
    # Resolve book
    book_obj = _resolve_book(book)

    # Load mapping and SZIT data
    mapping = load_book_mapping()
    szit_data = load_szit_json()

    # Get English name for this book
    english_name = None
    for eng, usx in mapping.items():
        if usx == book_obj.usx_code:
            english_name = eng
            break

    if english_name is None or english_name not in szit_data:
        console.print(f"[red]Book {book_obj.usx_code} not found in SZIT JSON[/red]")
        raise typer.Exit(code=1)

    book_data = szit_data[english_name]

    if chapter is not None:
        # Show specific chapter
        try:
            verses = get_chapter_verses(english_name, chapter, szit_data)
        except KeyError:
            console.print(
                f"[red]Chapter {chapter} not found in {book_obj.usx_code}[/red]"
            )
            raise typer.Exit(code=1)

        table = Table(title=f"{book_obj.hungarian_name} — Chapter {chapter}")
        table.add_column("Verse", justify="right", style="cyan")
        table.add_column("Text")

        for verse_num in sorted(verses.keys()):
            table.add_row(str(verse_num), verses[verse_num])

        console.print(table)
    else:
        # Show all chapters
        for chapter_key in sorted(book_data.keys(), key=int):
            chapter_num = int(chapter_key)
            verses = book_data[chapter_key]

            console.print(f"\n[bold]Chapter {chapter_num}[/bold]")
            table = Table()
            table.add_column("Verse", justify="right", style="cyan")
            table.add_column("Text")

            for verse_key in sorted(verses.keys(), key=int):
                table.add_row(verse_key, verses[verse_key])

            console.print(table)


@app.command()
def info(
    book_id: str = typer.Argument(help="USX code or Hungarian abbreviation"),
) -> None:
    """Show book info including chapter/verse counts."""
    book_obj = _resolve_book(book_id)

    schemas = load_versification()
    schema = get_versification(book_obj.usx_code, schemas)

    if schema is None:
        console.print(f"[red]No versification data for {book_obj.usx_code}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]{book_obj.usx_code}[/cyan] — {book_obj.hungarian_name}")
    console.print(f"  Abbreviation: {book_obj.abbreviation}")
    console.print(f"  Chapters: {schema.chapter_count}")
    console.print(f"  Testament: {book_obj.testament}")
    if book_obj.deuterocanonical:
        console.print("  [yellow]Deuterocanonical book[/yellow]")
