"""Scraper and parser for downloading and ingesting the Hungarian Catholic Bible from mek.oszk.hu.

Enables downloading, caching at the chapter level, parsing using BeautifulSoup,
and compiling a secondary flat JSONL corpus (mek.jsonl) for cross-source validation.
"""

from __future__ import annotations

from pathlib import Path

# Mapping from Paratext USX codes to mek.oszk.hu htm prefixes
USX_TO_MEK_PREFIX: dict[str, str] = {
    "GEN": "ter",
    "EXO": "kiv",
    "LEV": "lev",
    "NUM": "szam",
    "DEU": "mtorv",
    "JOS": "jozs",
    "JDG": "bir",
    "RUT": "rut",
    "1SA": "1sam",
    "2SA": "2sam",
    "1KI": "1kir",
    "2KI": "2kir",
    "1CH": "1kron",
    "2CH": "2kron",
    "EZR": "ezd",
    "NEH": "neh",
    "TOB": "tob",
    "JDT": "jud",
    "EST": "eszt",
    "1MA": "1mak",
    "2MA": "2mak",
    "JOB": "job",
    "PSA": "zsolt",
    "PRO": "peld",
    "ECC": "pred",
    "SNG": "en",
    "WIS": "bolcs",
    "SIR": "sir",
    "ISA": "iz",
    "JER": "jer",
    "LAM": "siral",
    "BAR": "bar",
    "EZK": "ez",
    "DAN": "dan",
    "HOS": "oz",
    "JOL": "jo",
    "AMO": "am",
    "OBA": "abd",
    "JON": "jon",
    "MIC": "mik",
    "NAM": "nah",
    "HAB": "hab",
    "ZEP": "szof",
    "HAG": "ag",
    "ZEC": "zak",
    "MAL": "mal",
    "MAT": "mt",
    "MRK": "mk",
    "LUK": "lk",
    "JHN": "jn",
    "ACT": "apcsel",
    "ROM": "rom",
    "1CO": "1kor",
    "2CO": "2kor",
    "GAL": "gal",
    "EPH": "ef",
    "PHP": "fil",
    "COL": "kol",
    "1TH": "1tessz",
    "2TH": "2tessz",
    "1TI": "1tim",
    "2TI": "2tim",
    "TIT": "tit",
    "PHM": "filem",
    "HEB": "zsid",
    "JAS": "jak",
    "1PE": "1pet",
    "2PE": "2pet",
    "1JN": "1jn",
    "2JN": "2jn",
    "3JN": "3jn",
    "JUD": "ju",
    "REV": "jel",
}


def download_mek_book(usx_code: str) -> str:
    """Download full book HTML from mek.oszk.hu and decode from Latin-2 (ISO-8859-2)."""
    raise NotImplementedError


def parse_and_cache_mek_chapters(
    usx_code: str,
    book_html: str,
    raw_dir: Path | None = None,
) -> list[Path]:
    """Split the full book HTML into chapter-level files and cache them as UTF-8."""
    raise NotImplementedError


def parse_mek_chapter(chapter_html: str) -> dict[int, str]:
    """Parse chapter-level HTML to extract verse numbers and text, combining suffix verses."""
    raise NotImplementedError


def build_mek_corpus(
    output_path: Path | None = None,
    data_dir: Path | None = None,
) -> int:
    """Download, cache, parse, and compile the full MEK Bible corpus to JSONL."""
    raise NotImplementedError
