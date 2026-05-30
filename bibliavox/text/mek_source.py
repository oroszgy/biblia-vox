"""Scraper and parser for downloading and ingesting the Hungarian Catholic Bible from mek.oszk.hu.

Enables downloading, caching at the chapter level, parsing using BeautifulSoup,
and compiling a secondary flat JSONL corpus (mek.jsonl) for cross-source validation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from bibliavox.reference.books import load_books
from bibliavox.text.normalizer import normalize_text

# Repo root: 3 levels up from bibliavox/text/mek_source.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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

# Regex to match a chapter header tag: e.g. <small><font color="AAAAAA"><p align=justify>Ter 1<BR></font></small>
# and distinguish it from verse tags like Ter 1.1
chapter_header_regex = re.compile(
    r"<small>\s*"
    r"<font[^>]*>\s*"
    r"(?:<p[^>]*>)?\s*"
    r"([1-3a-zA-Zá-źÁ-ŹíóőúűéáíóöőúüűÍÓŐÚŰÉÁÍÓÖŐÚÜŰ]+)\s+(\d+)\s*"
    r"<BR\s*/?>\s*"
    r"</font>\s*"
    r"</small>",
    re.IGNORECASE,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def download_mek_book(usx_code: str) -> str:
    """Download full book HTML from mek.oszk.hu and decode from Latin-2 (ISO-8859-2)."""
    usx_upper = usx_code.upper()
    if usx_upper not in USX_TO_MEK_PREFIX:
        raise ValueError(f"Unknown book USX code: {usx_code}")

    prefix = USX_TO_MEK_PREFIX[usx_upper]
    url = f"https://mek.oszk.hu/00100/00176/html/{prefix}.htm"

    # Use a strict 10.0s timeout to mitigate DoS (T-02.6-03)
    response = httpx.get(url, timeout=10.0)
    # Strictly check HTTP status codes (T-02.6-01)
    response.raise_for_status()
    return response.content.decode("iso-8859-2")


def parse_and_cache_mek_chapters(
    usx_code: str,
    book_html: str,
    raw_dir: Path | None = None,
) -> list[Path]:
    """Split the full book HTML into chapter-level files and cache them as UTF-8."""
    if raw_dir is None:
        raw_dir = _REPO_ROOT / "data" / "raw" / "text" / "mek"

    # Path traversal and input sanitization (T-02.6-02)
    usx_upper = usx_code.upper()
    if usx_upper not in USX_TO_MEK_PREFIX:
        raise ValueError(f"Unknown book USX code: {usx_code}")

    raw_dir.mkdir(parents=True, exist_ok=True)

    matches = list(chapter_header_regex.finditer(book_html))
    if not matches:
        # Graceful fallback for single-chapter books or formatting edge cases
        chapter_path = raw_dir / f"{usx_upper}_1.html"
        chapter_path.write_text(book_html, encoding="utf-8")
        return [chapter_path]

    cached_paths = []
    html_header = book_html[: matches[0].start()]

    for i, match in enumerate(matches):
        chapter_num = int(match.group(2))
        start_idx = match.start()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(book_html)

        chapter_content = book_html[start_idx:end_idx]

        # Re-assemble a simple valid HTML wrapper
        full_content = html_header + chapter_content
        if "</body>" not in chapter_content and "</body>" in book_html:
            full_content += "\n</body>\n</html>"

        chapter_path = raw_dir / f"{usx_upper}_{chapter_num}.html"
        chapter_path.write_text(full_content, encoding="utf-8")
        cached_paths.append(chapter_path)

    return cached_paths


def parse_tag_text(text: str) -> tuple[int, int | None] | None:
    """Parse text inside a small tag into (chapter_num, verse_num)."""
    text = text.strip()
    if not text:
        return None
    parts = text.split()
    if not parts:
        return None
    ref = parts[-1]
    if "." in ref:
        ch_str, v_str = ref.split(".", 1)
        if not ch_str.isdigit():
            return None
        # Extract leading digits of the verse part to ignore letter suffixes (like 4a, 4b)
        v_match = re.match(r"^(\d+)", v_str)
        if not v_match:
            return None
        return int(ch_str), int(v_match.group(1))
    else:
        if ref.isdigit():
            return int(ref), None
    return None


def parse_mek_chapter(chapter_html: str) -> dict[int, str]:
    """Parse chapter-level HTML to extract verse numbers and text, combining suffix verses."""
    soup = BeautifulSoup(chapter_html, "html.parser")
    verses: dict[int, list[str]] = {}

    small_tags = soup.find_all("small")
    for tag in small_tags:
        parsed = parse_tag_text(tag.get_text())
        if parsed is None:
            continue

        _, v_num = parsed
        if v_num is None:
            # It's a chapter header, not a verse tag
            continue

        # Extract all text following this verse tag until the next small tag
        verse_texts = []
        for sibling in tag.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name == "small":
                    break
                # Accumulate text content of inner formatting tags (like <b>, <i>, etc.)
                # and do not execute scripts/css (T-02.6-01)
                if sibling.name not in ("script", "style"):
                    verse_texts.append(sibling.get_text())
            elif isinstance(sibling, NavigableString):
                verse_texts.append(str(sibling))

        verse_raw_text = "".join(verse_texts)
        verse_text = normalize_text(verse_raw_text)
        if verse_text:
            if v_num not in verses:
                verses[v_num] = []
            verses[v_num].append(verse_text)

    # Combine suffix verses (like 2.4a and 2.4b) with space
    final_verses: dict[int, str] = {}
    for v_num, text_list in verses.items():
        combined_text = normalize_text(" ".join(text_list))
        final_verses[v_num] = combined_text

    return final_verses


def build_mek_corpus(
    output_path: Path | None = None,
    data_dir: Path | None = None,
) -> int:
    """Download, cache, parse, and compile the full MEK Bible corpus to JSONL."""
    if output_path is None:
        output_path = _REPO_ROOT / "data" / "processed" / "text" / "mek.jsonl"

    if data_dir is None:
        data_dir = _REPO_ROOT / "data"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_mek_dir = data_dir / "raw" / "text" / "mek"
    raw_mek_dir.mkdir(parents=True, exist_ok=True)

    ref_dir = data_dir / "reference" if data_dir is not None else None
    books = load_books(data_dir=ref_dir)

    total_verses_written = 0

    with open(output_path, "w", encoding="utf-8") as f_out:
        for book in books:
            usx_code = book.usx_code.upper()
            if usx_code not in USX_TO_MEK_PREFIX:
                # Missing book on MEK is logged and skipped gracefully (D-03)
                continue

            # Check if we have cached chapter files for this book
            cached_chapters = sorted(
                raw_mek_dir.glob(f"{usx_code}_*.html"),
                key=lambda p: (
                    int(p.stem.split("_")[-1]) if p.stem.split("_")[-1].isdigit() else 0
                ),
            )

            if not cached_chapters:
                try:
                    book_html = download_mek_book(usx_code)
                    cached_chapters = parse_and_cache_mek_chapters(
                        usx_code=usx_code,
                        book_html=book_html,
                        raw_dir=raw_mek_dir,
                    )
                except Exception as e:
                    # Report missing books/chapters gracefully without interrupting the pipeline
                    print(
                        f"Warning: Gracefully skipped book {usx_code} due to ingestion error: {e}"
                    )
                    continue

            for ch_path in cached_chapters:
                try:
                    chapter_num = int(ch_path.stem.split("_")[-1])
                except ValueError:
                    continue

                ch_html = ch_path.read_text(encoding="utf-8")
                verses = parse_mek_chapter(ch_html)

                # Write sorted verses
                for v_num in sorted(verses.keys()):
                    record = {
                        "book": usx_code,
                        "chapter": chapter_num,
                        "verse": v_num,
                        "text": verses[v_num],
                    }
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_verses_written += 1

    return total_verses_written
