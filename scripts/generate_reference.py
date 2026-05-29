#!/usr/bin/env python3
"""Generate static reference JSON files from szentiras.eu tdverse data.

This script fetches the tdverse.csv from the szentiras.eu GitHub repository
and produces two static JSON files:
- data/reference/books.json — 73-book Catholic Bible catalog
- data/reference/versification.json — Chapter/verse counts per book

Usage:
    uv run python scripts/generate_reference.py
    uv run python scripts/generate_reference.py --source /path/to/tdverse.csv

The generated JSON files are committed to the repository and loaded at runtime
(no network dependency). Re-run this script only when the source data changes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Default source URL for the tdverse.csv data
DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/szentiras/szentiras.hu/main/data/tdverse.csv"
)

# Repo root: parent of scripts/ directory
_REPO_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_DIR = _REPO_ROOT / "data" / "reference"

# Catholic book ordering (Vulgate order) with USX codes and Hungarian metadata.
# Book numbers match the gepi encoding: {bookNum}{chapter:3d}{verse:3d}00
BOOK_METADATA: list[dict] = [
    # Pentateuch
    {"usx_code": "GEN", "hungarian_name": "Teremtés könyve", "abbreviation": "Ter", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "EXO", "hungarian_name": "Kivonulás könyve", "abbreviation": "Kiv", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "LEV", "hungarian_name": "Leviták könyve", "abbreviation": "Lev", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "NUM", "hungarian_name": "Számok könyve", "abbreviation": "Szám", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "DEU", "hungarian_name": "Második törvénykönyv", "abbreviation": "MTörv", "testament": "OT", "deuterocanonical": False},
    # Historical books
    {"usx_code": "JOS", "hungarian_name": "Józsué könyve", "abbreviation": "Józs", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "JDG", "hungarian_name": "Bírák könyve", "abbreviation": "Bír", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "RUT", "hungarian_name": "Ruth könyve", "abbreviation": "Ruth", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "1SA", "hungarian_name": "Sámuel első könyve", "abbreviation": "Sám1", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "2SA", "hungarian_name": "Sámuel második könyve", "abbreviation": "Sám2", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "1KI", "hungarian_name": "Királyok első könyve", "abbreviation": "Kir1", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "2KI", "hungarian_name": "Királyok második könyve", "abbreviation": "Kir2", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "1CH", "hungarian_name": "Krónikák első könyve", "abbreviation": "Krón1", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "2CH", "hungarian_name": "Krónikák második könyve", "abbreviation": "Krón2", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "EZR", "hungarian_name": "Ezdrás könyve", "abbreviation": "Ezd", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "NEH", "hungarian_name": "Nehemiás könyve", "abbreviation": "Neh", "testament": "OT", "deuterocanonical": False},
    # Deuterocanonical (OT)
    {"usx_code": "TOB", "hungarian_name": "Tóbiás könyve", "abbreviation": "Tób", "testament": "OT", "deuterocanonical": True},
    {"usx_code": "JDT", "hungarian_name": "Judit könyve", "abbreviation": "Jdt", "testament": "OT", "deuterocanonical": True},
    {"usx_code": "EST", "hungarian_name": "Eszter könyve", "abbreviation": "Esz", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "1MA", "hungarian_name": "Makkabeusok első könyve", "abbreviation": "Mak1", "testament": "OT", "deuterocanonical": True},
    {"usx_code": "2MA", "hungarian_name": "Makkabeusok második könyve", "abbreviation": "Mak2", "testament": "OT", "deuterocanonical": True},
    # Wisdom/Poetry
    {"usx_code": "JOB", "hungarian_name": "Jób könyve", "abbreviation": "Jób", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "PSA", "hungarian_name": "Zsoltárok könyve", "abbreviation": "Zsolt", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "PRO", "hungarian_name": "Példabeszédek könyve", "abbreviation": "Péld", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "ECC", "hungarian_name": "Prédikátor könyve", "abbreviation": "Préd", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "SNG", "hungarian_name": "Énekek éneke", "abbreviation": "Én", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "WIS", "hungarian_name": "Bölcsesség könyve", "abbreviation": "Bölcs", "testament": "OT", "deuterocanonical": True},
    {"usx_code": "SIR", "hungarian_name": "Sirák fia könyve", "abbreviation": "Sir", "testament": "OT", "deuterocanonical": True},
    # Major prophets
    {"usx_code": "ISA", "hungarian_name": "Izajás könyve", "abbreviation": "Iz", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "JER", "hungarian_name": "Jeremiás könyve", "abbreviation": "Jer", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "LAM", "hungarian_name": "Jeremiás siralmai", "abbreviation": "Siralm", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "BAR", "hungarian_name": "Báruch könyve", "abbreviation": "Bár", "testament": "OT", "deuterocanonical": True},
    {"usx_code": "EZK", "hungarian_name": "Ezekiel könyve", "abbreviation": "Ez", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "DAN", "hungarian_name": "Dániel könyve", "abbreviation": "Dán", "testament": "OT", "deuterocanonical": False},
    # Minor prophets
    {"usx_code": "HOS", "hungarian_name": "Hóseás könyve", "abbreviation": "Hós", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "JOL", "hungarian_name": "Joél könyve", "abbreviation": "Joél", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "AMO", "hungarian_name": "Ámós könyve", "abbreviation": "Ám", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "OBA", "hungarian_name": "Abdiás könyve", "abbreviation": "Abd", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "JON", "hungarian_name": "Jónás könyve", "abbreviation": "Jón", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "MIC", "hungarian_name": "Mikeás könyve", "abbreviation": "Mik", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "NAM", "hungarian_name": "Náhum könyve", "abbreviation": "Náh", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "HAB", "hungarian_name": "Habakuk könyve", "abbreviation": "Hab", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "ZEP", "hungarian_name": "Sofóniás könyve", "abbreviation": "Sof", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "HAG", "hungarian_name": "Aggeus könyve", "abbreviation": "Ag", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "ZEC", "hungarian_name": "Zakariás könyve", "abbreviation": "Zak", "testament": "OT", "deuterocanonical": False},
    {"usx_code": "MAL", "hungarian_name": "Malakiás könyve", "abbreviation": "Mal", "testament": "OT", "deuterocanonical": False},
    # Gospels
    {"usx_code": "MAT", "hungarian_name": "Máté evangéliuma", "abbreviation": "Mt", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "MRK", "hungarian_name": "Márk evangéliuma", "abbreviation": "Mk", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "LUK", "hungarian_name": "Lukács evangéliuma", "abbreviation": "Lk", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "JHN", "hungarian_name": "János evangéliuma", "abbreviation": "Jn", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "ACT", "hungarian_name": "Apostolok cselekedetei", "abbreviation": "ApCsel", "testament": "NT", "deuterocanonical": False},
    # Pauline epistles
    {"usx_code": "ROM", "hungarian_name": "Rómabeliekhez írt levél", "abbreviation": "Róm", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "1CO", "hungarian_name": "Korinthusiakhoz írt első levél", "abbreviation": "1Kor", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "2CO", "hungarian_name": "Korinthusiakhoz írt második levél", "abbreviation": "2Kor", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "GAL", "hungarian_name": "Galatáknak írt levél", "abbreviation": "Gal", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "EPH", "hungarian_name": "Efezusiaknak írt levél", "abbreviation": "Ef", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "PHP", "hungarian_name": "Filippiekhez írt levél", "abbreviation": "Fil", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "COL", "hungarian_name": "Kolosszeiekhez írt levél", "abbreviation": "Kol", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "1TH", "hungarian_name": "Thesszalonikiakhoz írt első levél", "abbreviation": "1Tessz", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "2TH", "hungarian_name": "Thesszalonikiakhoz írt második levél", "abbreviation": "2Tessz", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "1TI", "hungarian_name": "Timóteusnak írt első levél", "abbreviation": "1Tim", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "2TI", "hungarian_name": "Timóteusnak írt második levél", "abbreviation": "2Tim", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "TIT", "hungarian_name": "Tituszhoz írt levél", "abbreviation": "Tit", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "PHM", "hungarian_name": "Filemonhoz írt levél", "abbreviation": "Filem", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "HEB", "hungarian_name": "Zsidóknak írt levél", "abbreviation": "Zsid", "testament": "NT", "deuterocanonical": False},
    # Catholic epistles
    {"usx_code": "JAS", "hungarian_name": "Jakab levele", "abbreviation": "Jak", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "1PE", "hungarian_name": "Péter első levele", "abbreviation": "1Pt", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "2PE", "hungarian_name": "Péter második levele", "abbreviation": "2Pt", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "1JN", "hungarian_name": "János első levele", "abbreviation": "1Jn", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "2JN", "hungarian_name": "János második levele", "abbreviation": "2Jn", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "3JN", "hungarian_name": "János harmadik levele", "abbreviation": "3Jn", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "JUD", "hungarian_name": "Júdás levele", "abbreviation": "Júd", "testament": "NT", "deuterocanonical": False},
    {"usx_code": "REV", "hungarian_name": "János jelenései", "abbreviation": "Jel", "testament": "NT", "deuterocanonical": False},
]

# Book number mapping (gepi encoding base: {bookNum}{chapter:3d}{verse:3d}00)
BOOK_NUMBERS: dict[str, int] = {
    "GEN": 101, "EXO": 102, "LEV": 103, "NUM": 104, "DEU": 105,
    "JOS": 106, "JDG": 107, "RUT": 108, "1SA": 109, "2SA": 110,
    "1KI": 111, "2KI": 112, "1CH": 113, "2CH": 114, "EZR": 115,
    "NEH": 116, "TOB": 117, "JDT": 118, "EST": 119, "1MA": 120,
    "2MA": 121, "JOB": 122, "PSA": 123, "PRO": 124, "ECC": 125,
    "SNG": 126, "WIS": 127, "SIR": 128, "ISA": 129, "JER": 130,
    "LAM": 131, "BAR": 132, "EZK": 133, "DAN": 134, "HOS": 135,
    "JOL": 136, "AMO": 137, "OBA": 138, "JON": 139, "MIC": 140,
    "NAM": 141, "HAB": 142, "ZEP": 143, "HAG": 144, "ZEC": 145,
    "MAL": 146, "MAT": 401, "MRK": 402, "LUK": 403, "JHN": 404,
    "ACT": 405, "ROM": 406, "1CO": 407, "2CO": 408, "GAL": 409,
    "EPH": 410, "PHP": 411, "COL": 412, "1TH": 413, "2TH": 414,
    "1TI": 415, "2TI": 416, "TIT": 417, "PHM": 418, "HEB": 419,
    "JAS": 420, "1PE": 421, "2PE": 422, "1JN": 423, "2JN": 424,
    "3JN": 425, "JUD": 426, "REV": 427,
}


def fetch_tdverse_from_url(url: str) -> list[dict]:
    """Fetch tdverse.csv from a URL and parse it."""
    import urllib.request

    print(f"Fetching tdverse data from: {url}")
    with urllib.request.urlopen(url) as response:
        content = response.read().decode("utf-8")
    return list(csv.DictReader(content.splitlines()))


def load_tdverse_from_file(path: Path) -> list[dict]:
    """Load tdverse.csv from a local file."""
    print(f"Loading tdverse data from: {path}")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_gepi(gepi: str) -> tuple[int, int, int]:
    """Parse a gepi code into (book_number, chapter, verse).

    Gepi format: {bookNum}{chapter:3d}{verse:3d}00
    Example: 10100103100 → (101, 1, 31)
    """
    gepi_str = str(int(gepi))  # Normalize: remove leading zeros
    # Book number is first 3 digits
    book_num = int(gepi_str[:3])
    # Chapter is next 3 digits
    chapter = int(gepi_str[3:6])
    # Verse is next 3 digits
    verse = int(gepi_str[6:9])
    return book_num, chapter, verse


def build_versification(rows: list[dict]) -> dict[str, dict]:
    """Build versification data from tdverse rows.

    Returns: {usx_code: {"chapter_count": N, "chapters": {1: verse_count, ...}}}
    """
    # Collect verse data: {(book_num, chapter): max_verse}
    chapter_verses: dict[tuple[int, int], int] = defaultdict(int)
    book_num_set: set[int] = set()

    for row in rows:
        gepi = row.get("gepi", "")
        if not gepi:
            continue
        try:
            book_num, chapter, verse = parse_gepi(gepi)
        except (ValueError, IndexError):
            continue
        book_num_set.add(book_num)
        key = (book_num, chapter)
        if verse > chapter_verses[key]:
            chapter_verses[key] = verse

    # Map book_num → usx_code
    num_to_usx = {v: k for k, v in BOOK_NUMBERS.items()}

    result = {}
    for book_num in sorted(book_num_set):
        usx_code = num_to_usx.get(book_num)
        if usx_code is None:
            print(f"  Warning: Unknown book number {book_num}, skipping")
            continue

        # Get all chapters for this book
        book_chapters = {
            ch: verse
            for (bn, ch), verse in chapter_verses.items()
            if bn == book_num
        }
        if not book_chapters:
            continue

        chapter_count = max(book_chapters.keys())
        result[usx_code] = {
            "chapter_count": chapter_count,
            "chapters": {str(ch): book_chapters[ch] for ch in sorted(book_chapters)},
        }

    return result


def write_books_json(output_dir: Path) -> int:
    """Write books.json with book_number fields populated."""
    books = []
    for meta in BOOK_METADATA:
        entry = dict(meta)
        entry["book_number"] = BOOK_NUMBERS[meta["usx_code"]]
        books.append(entry)

    output_path = output_dir / "books.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return len(books)


def write_versification_json(output_dir: Path, versification: dict[str, dict]) -> int:
    """Write versification.json from computed versification data."""
    # Merge with BOOK_METADATA to ensure all 73 books are present
    result = []
    for meta in BOOK_METADATA:
        usx = meta["usx_code"]
        if usx in versification:
            entry = {"usx_code": usx, **versification[usx]}
            result.append(entry)
        else:
            print(f"  Warning: No versification data for {usx}")

    output_path = output_dir / "versification.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return len(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reference JSON files from szentiras.eu tdverse data."
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to local tdverse.csv file. If not provided, fetches from GitHub.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(_OUTPUT_DIR),
        help="Output directory for JSON files (default: data/reference/).",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load tdverse data
    if args.source:
        rows = load_tdverse_from_file(Path(args.source))
    else:
        try:
            rows = fetch_tdverse_from_url(DEFAULT_SOURCE_URL)
        except Exception as e:
            print(f"Error fetching from URL: {e}")
            print("Use --source to provide a local tdverse.csv file.")
            sys.exit(1)

    print(f"Loaded {len(rows)} tdverse rows")

    # Build versification from tdverse
    versification = build_versification(rows)
    print(f"Built versification for {len(versification)} books")

    # Write output files
    book_count = write_books_json(output_dir)
    versification_count = write_versification_json(output_dir, versification)

    print(
        f"Generated books.json ({book_count} books) "
        f"and versification.json ({versification_count} books)"
    )


if __name__ == "__main__":
    main()
