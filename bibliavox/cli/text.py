"""Text subcommand group for Bible text operations.

Commands:
    fetch         — Fetch and display Bible text by book/chapter
    info          — Show book info including chapter/verse counts
    validate      — Validate verse counts against versification schema
    normalize     — Normalize Bible text (NFC, whitespace, line endings)
    convert-jsonl — Convert SZIT JSON to JSONL format with USX codes
    fix-verses    — Fix embedded verse markers in JSONL
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from bibliavox.reference.books import lookup_by_abbreviation, lookup_by_usx_code
from bibliavox.reference.schema import get_versification, load_versification
from bibliavox.text.mapping import load_book_mapping
from bibliavox.text.normalizer import normalize_chapter
from bibliavox.text.source import get_chapter_verses, load_szit_json
from bibliavox.text.validator import generate_report, validate_book, validate_chapter

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
                table.add_row(str(verse_key), verses[verse_key])

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


@app.command()
def validate(
    book: str | None = typer.Option(
        None, "--book", "-b", help="USX code or Hungarian abbreviation"
    ),
    chapter: int | None = typer.Option(
        None, "--chapter", "-c", help="Chapter number (omit for all)"
    ),
    all_books: bool = typer.Option(False, "--all", "-a", help="Validate all books"),
    strict_missing_chapters: bool = typer.Option(
        False,
        "--strict-missing-chapters",
        help="Fail when expected chapters are missing from source text",
    ),
) -> None:
    """Validate verse counts against versification schema."""
    if not book and not all_books:
        console.print("[red]Specify --book or --all[/red]")
        raise typer.Exit(code=1)

    schemas = load_versification()
    mapping = load_book_mapping()
    szit_data = load_szit_json()

    if all_books:
        # Validate all books
        all_discrepancies = []
        books_checked = 0
        books_passed = 0

        for english_name, usx_code in mapping.items():
            if english_name not in szit_data:
                console.print(
                    f"[yellow]Skipping {usx_code} — not in SZIT JSON[/yellow]"
                )
                continue

            books_checked += 1
            discrepancies = validate_book(
                usx_code,
                szit_data,
                mapping,
                schemas,
                strict_missing_chapters=strict_missing_chapters,
            )

            if not discrepancies:
                books_passed += 1
                console.print(f"[green]✓ {usx_code}[/green]")
            else:
                all_discrepancies.extend(discrepancies)
                console.print(
                    f"[red]✗ {usx_code} — {len(discrepancies)} discrepancy(ies)[/red]"
                )

        console.print(
            f"\n[bold]Summary:[/bold] {books_passed}/{books_checked} books passed validation"
        )

        if all_discrepancies:
            # Display all discrepancies
            table = Table(title="All Validation Discrepancies")
            table.add_column("Book", style="cyan")
            table.add_column("Chapter", justify="right")
            table.add_column("Verse", justify="right")
            table.add_column("Severity", style="yellow")
            table.add_column("Details")

            for d in all_discrepancies:
                severity_style = "red" if d.severity.value == "ERROR" else "yellow"
                table.add_row(
                    d.book,
                    str(d.chapter),
                    str(d.verse) if d.verse is not None else "—",
                    f"[{severity_style}]{d.severity.value}[/{severity_style}]",
                    d.details,
                )

            console.print(table)

            # Also output JSON report
            report = generate_report(all_discrepancies)
            console.print("\n[dim]JSON Report:[/dim]")
            console.print(report)
        return

    # Validate single book
    book_obj = _resolve_book(str(book))

    # Get English name for this book
    english_name = None
    for eng, usx in mapping.items():
        if usx == book_obj.usx_code:
            english_name = eng
            break

    if english_name is None or english_name not in szit_data:
        console.print(f"[red]Book {book_obj.usx_code} not found in SZIT JSON[/red]")
        raise typer.Exit(code=1)

    if chapter is not None:
        # Validate specific chapter
        try:
            verses = get_chapter_verses(english_name, chapter, szit_data)
        except KeyError:
            console.print(
                f"[red]Chapter {chapter} not found in {book_obj.usx_code}[/red]"
            )
            raise typer.Exit(code=1)

        discrepancies = validate_chapter(book_obj.usx_code, chapter, verses, schemas)
    else:
        # Validate entire book
        discrepancies = validate_book(
            book_obj.usx_code,
            szit_data,
            mapping,
            schemas,
            strict_missing_chapters=strict_missing_chapters,
        )

    if not discrepancies:
        console.print(
            f"[green]✓ {book_obj.usx_code} validation passed — no discrepancies[/green]"
        )
        return

    # Display discrepancies
    table = Table(title=f"Validation Results — {book_obj.usx_code}")
    table.add_column("Book", style="cyan")
    table.add_column("Chapter", justify="right")
    table.add_column("Verse", justify="right")
    table.add_column("Severity", style="yellow")
    table.add_column("Details")

    for d in discrepancies:
        severity_style = "red" if d.severity.value == "ERROR" else "yellow"
        table.add_row(
            d.book,
            str(d.chapter),
            str(d.verse) if d.verse is not None else "—",
            f"[{severity_style}]{d.severity.value}[/{severity_style}]",
            d.details,
        )

    console.print(table)

    # Also output JSON report
    report = generate_report(discrepancies)
    console.print("\n[dim]JSON Report:[/dim]")
    console.print(report)


@app.command()
def normalize(
    book: str | None = typer.Option(
        None, "--book", "-b", help="USX code or Hungarian abbreviation"
    ),
    all_books: bool = typer.Option(False, "--all", "-a", help="Normalize all books"),
) -> None:
    """Normalize Bible text (NFC, whitespace, line endings)."""
    if not book and not all_books:
        console.print("[red]Specify --book or --all[/red]")
        raise typer.Exit(code=1)

    mapping = load_book_mapping()
    szit_data = load_szit_json()

    if all_books:
        # Normalize all books
        books_to_normalize = list(mapping.keys())
    else:
        # Normalize specific book
        book_obj = _resolve_book(str(book))
        english_name = None
        for eng, usx in mapping.items():
            if usx == book_obj.usx_code:
                english_name = eng
                break
        if english_name is None:
            console.print(f"[red]Book {book_obj.usx_code} not found in mapping[/red]")
            raise typer.Exit(code=1)
        books_to_normalize = [english_name]

    console.print(f"[cyan]Normalizing {len(books_to_normalize)} book(s)...[/cyan]")

    for eng_name in books_to_normalize:
        if eng_name not in szit_data:
            console.print(f"[yellow]Skipping {eng_name} — not in SZIT JSON[/yellow]")
            continue

        usx_code = mapping[eng_name]
        book_data = szit_data[eng_name]
        normalized_book = {}

        for chapter_str, verses_data in book_data.items():
            chapter = int(chapter_str)
            verses = {int(k): v for k, v in verses_data.items()}
            normalized_book[chapter] = normalize_chapter(verses)

        # Save to data/processed/text/{usx_code}.json
        from pathlib import Path

        output_dir = Path("data/processed/text")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{usx_code}.json"

        import json

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(normalized_book, f, ensure_ascii=False, indent=2)

        console.print(f"  ✓ {usx_code} → {output_path}")

    console.print("[green]Normalization complete[/green]")


@app.command()
def convert_jsonl(
    output: Path = typer.Option(
        Path("data/processed/text/szit.jsonl"),
        "--output",
        "-o",
        help="Output JSONL path",
    ),
) -> None:
    """Convert SZIT JSON to JSONL format with USX codes."""
    from bibliavox.text.jsonl_converter import convert_to_jsonl

    output.parent.mkdir(parents=True, exist_ok=True)
    count = convert_to_jsonl(output)
    console.print(f"[green]✓ Wrote {count} verses to {output}[/green]")


@app.command()
def fix_verses(
    input_path: Path = typer.Option(
        Path("data/processed/text/szit.jsonl"),
        "--input",
        "-i",
        help="Input JSONL path",
    ),
    output: Path = typer.Option(
        Path("data/processed/text/szit-fixed.jsonl"),
        "--output",
        "-o",
        help="Output JSONL path",
    ),
) -> None:
    """Fix embedded verse markers in JSONL file."""
    from bibliavox.text.splitter import fix_verses as split_verses

    stats = split_verses(input_path, output)
    console.print(
        f"[green]✓ Fixed verses: {stats['cleaned']} cleaned, "
        f"{stats['split']} split, {stats['unchanged']} unchanged[/green]"
    )
    console.print(f"[green]✓ Output: {output}[/green]")


@app.command()
def ingest_mek(
    output: Path = typer.Option(
        Path("data/processed/text/mek.jsonl"),
        "--output",
        "-o",
        help="Output JSONL path",
    ),
) -> None:
    """Download and parse MEK HTML text into a flat JSONL corpus."""
    from bibliavox.text.mek_source import build_mek_corpus

    console.print("[cyan]Ingesting MEK alternate text source (all 73 books)...[/cyan]")
    count = build_mek_corpus(output)
    console.print(f"[green]✓ Successfully wrote {count} verses to {output}[/green]")


@app.command()
def cross_validate(
    szit: Path = typer.Option(
        Path("data/processed/text/szit-fixed.jsonl"),
        "--szit",
        "-s",
        help="Path to fixed SZIT JSONL corpus",
    ),
    mek: Path = typer.Option(
        Path("data/processed/text/mek.jsonl"),
        "--mek",
        "-m",
        help="Path to parsed MEK JSONL corpus",
    ),
    output_diff: Path = typer.Option(
        Path("data/processed/text/text-discrepancies.jsonl"),
        "--output-diff",
        "-o",
        help="Path to output JSONL discrepancy file",
    ),
) -> None:
    """Cross-validate SZIT vs MEK corpora, flagging all coverage and textual discrepancies."""
    from bibliavox.text.cross_validator import cross_validate_corpora

    if not szit.exists():
        console.print(f"[red]Error: SZIT corpus not found at {szit}[/red]")
        raise typer.Exit(code=1)
    if not mek.exists():
        console.print(f"[red]Error: MEK corpus not found at {mek}[/red]")
        raise typer.Exit(code=1)

    console.print("[cyan]Cross-validating corpora...[/cyan]")
    console.print(f"  SZIT: {szit}")
    console.print(f"  MEK:  {mek}")

    discrepancies = cross_validate_corpora(szit, mek)

    # 1. Compute summary counts by type/severity
    summary = {
        "missing_book": 0,
        "missing_chapter": 0,
        "missing_verse": 0,
        "text_diff": 0,
    }
    for d in discrepancies:
        t = d["type"]
        if t in summary:
            summary[t] += 1

    # 2. Render Rich summary table
    summary_table = Table(title="Discrepancy Summary by Type")
    summary_table.add_column("Discrepancy Type", style="cyan")
    summary_table.add_column("Severity", style="yellow")
    summary_table.add_column("Count", justify="right", style="magenta")

    for d_type, count in summary.items():
        summary_table.add_row(d_type, d_type, str(count))

    console.print(summary_table)

    # 3. Write all discrepancies to JSONL output
    output_diff.parent.mkdir(parents=True, exist_ok=True)
    with open(output_diff, "w", encoding="utf-8") as f:
        for d in discrepancies:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    console.print(
        f"[green]✓ Wrote {len(discrepancies)} discrepancy records to {output_diff}[/green]"
    )

    # 4. If discrepancies found, list detail rows in a beautiful Rich Table (limited to 100 rows)
    if discrepancies:
        detail_table = Table(title="Discrepancy Details (Showing first 100)")
        detail_table.add_column("Book", style="cyan")
        detail_table.add_column("Chapter", justify="right")
        detail_table.add_column("Verse", justify="right")
        detail_table.add_column("Type", style="yellow")
        detail_table.add_column("Source Lacking", style="red")
        detail_table.add_column("Details")

        for d in discrepancies[:100]:
            ref = f"{d['book']}"
            ch_str = str(d["chapter"]) if d["chapter"] is not None else "—"
            v_str = str(d["verse"]) if d["verse"] is not None else "—"

            # Formulate friendly details
            details_text = ""
            if d["type"] == "missing_book":
                details_text = (
                    f"Book {d['book']} is completely missing in {d['source']}"
                )
            elif d["type"] == "missing_chapter":
                details_text = f"Chapter {d['chapter']} is missing in {d['source']}"
            elif d["type"] == "missing_verse":
                details_text = f"Verse {d['verse']} is missing in {d['source']}"
            elif d["type"] == "text_diff":
                sz_short = (
                    d["szit_text"][:25] + "..."
                    if len(d["szit_text"]) > 25
                    else d["szit_text"]
                )
                mk_short = (
                    d["mek_text"][:25] + "..."
                    if len(d["mek_text"]) > 25
                    else d["mek_text"]
                )
                details_text = f"SZIT: {sz_short} | MEK: {mk_short}"

            detail_table.add_row(
                ref,
                ch_str,
                v_str,
                d["type"],
                d["source"],
                details_text,
            )

        console.print(detail_table)
        if len(discrepancies) > 100:
            console.print(
                f"[yellow]Note: Truncated {len(discrepancies) - 100} detailed rows from stdout view.[/yellow]"
            )
