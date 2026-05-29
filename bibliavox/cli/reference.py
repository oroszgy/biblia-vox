"""Reference subcommand group for Bible book and versification lookups.

Commands:
    list      — List all 73 Catholic Bible books
    lookup    — Look up a book by Hungarian abbreviation
    info      — Show detailed info including chapter/verse counts
    generate  — Generate reference JSON files from szentiras.eu source
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from bibliavox.reference.books import (
    get_all_books,
    lookup_by_abbreviation,
    lookup_by_usx_code,
)
from bibliavox.reference.generate import app as generate_app
from bibliavox.reference.schema import (
    get_chapter_count,
    get_versification,
    load_versification,
)

app = typer.Typer(name="reference", help="Bible reference data operations")
app.add_typer(generate_app, name="generate")
console = Console()


@app.command(name="list")
def list_books(
    testament: str = typer.Option(
        None, "--testament", "-t", help="Filter by testament: OT or NT"
    ),
    deuterocanonical: bool = typer.Option(
        False, "--deuterocanonical", "-d", help="Show only deuterocanonical books"
    ),
) -> None:
    """List all 73 Catholic Bible books."""
    books = get_all_books()
    if testament:
        books = [b for b in books if b.testament == testament.upper()]
    if deuterocanonical:
        books = [b for b in books if b.deuterocanonical]

    table = Table(title=f"Catholic Bible Books ({len(books)})")
    table.add_column("USX", style="cyan")
    table.add_column("Hungarian Name", style="green")
    table.add_column("Abbreviation", style="yellow")
    table.add_column("Number", justify="right")
    table.add_column("Testament")
    table.add_column("Deutero", justify="center")

    for book in books:
        table.add_row(
            book.usx_code,
            book.hungarian_name,
            book.abbreviation,
            str(book.book_number),
            book.testament,
            "✓" if book.deuterocanonical else "",
        )
    console.print(table)


@app.command()
def lookup(
    abbreviation: str = typer.Argument(
        help="Hungarian book abbreviation (e.g., Ter, Mk, Jn)"
    ),
) -> None:
    """Look up a book by Hungarian abbreviation."""
    book = lookup_by_abbreviation(abbreviation)
    if book is None:
        console.print(f"[red]Unknown abbreviation: {abbreviation}[/red]")
        raise typer.Exit(code=1)

    schemas = load_versification()
    chapter_count = get_chapter_count(book.usx_code, schemas)

    console.print(f"[cyan]{book.usx_code}[/cyan] — {book.hungarian_name}")
    console.print(f"  Abbreviation: {book.abbreviation}")
    console.print(f"  Book number:  {book.book_number}")
    console.print(f"  Testament:    {book.testament}")
    console.print(f"  Chapters:     {chapter_count}")
    if book.deuterocanonical:
        console.print("  [yellow]Deuterocanonical book[/yellow]")


@app.command()
def info(
    book_id: str = typer.Argument(
        help="USX code or Hungarian abbreviation (e.g., GEN or Ter)"
    ),
) -> None:
    """Show detailed info for a book including chapter/verse counts."""
    # Try USX code first, then abbreviation
    book = lookup_by_usx_code(book_id)
    if book is None:
        book = lookup_by_abbreviation(book_id)
    if book is None:
        console.print(f"[red]Unknown book: {book_id}[/red]")
        raise typer.Exit(code=1)

    schema = get_versification(book.usx_code)
    if schema is None:
        console.print(f"[red]No versification data for {book.usx_code}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[cyan]{book.usx_code}[/cyan] — {book.hungarian_name}")
    console.print(f"  Chapters: {schema.chapter_count}")
    console.print()

    table = Table(title=f"Verse Counts — {book.hungarian_name}")
    table.add_column("Chapter", justify="right", style="cyan")
    table.add_column("Verses", justify="right")

    for ch_num, verse_count in sorted(schema.chapters.items(), key=lambda x: int(x[0])):
        table.add_row(str(ch_num), str(verse_count))

    console.print(table)
