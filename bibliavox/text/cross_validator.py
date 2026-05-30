"""Cross-source completeness and coverage validation engine."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path


def normalize_and_collapse(text: str) -> str:
    """Normalize Unicode to NFC form and collapse all consecutive whitespace."""
    nfc_text = unicodedata.normalize("NFC", text)
    return " ".join(nfc_text.split())


def load_jsonl_corpus(path: Path) -> dict[str, dict[int, dict[int, str]]]:
    """Load a JSONL corpus, indexing by book, chapter, and verse.

    Handles JSONDecodeError and missing/invalid keys gracefully.
    """
    corpus_data: dict[str, dict[int, dict[int, str]]] = {}
    if not path.exists():
        return corpus_data

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                book = record["book"]
                chapter = int(record["chapter"])
                verse = int(record["verse"])
                text = record["text"]

                if book not in corpus_data:
                    corpus_data[book] = {}
                if chapter not in corpus_data[book]:
                    corpus_data[book][chapter] = {}
                corpus_data[book][chapter][verse] = text
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                # Handle JSONDecodeError and other malformed entries gracefully
                continue

    return corpus_data


def cross_validate_corpora(szit_path: Path, mek_path: Path) -> list[dict]:
    """Compare fixed SZIT and parsed MEK corpora.

    Identifies coverage gaps (missing books, chapters, verses) and textual discrepancies.
    Returns a list of flat discrepancy records.
    """
    szit_data = load_jsonl_corpus(szit_path)
    mek_data = load_jsonl_corpus(mek_path)

    discrepancies: list[dict] = []

    all_books = sorted(list(set(szit_data.keys()) | set(mek_data.keys())))

    for book in all_books:
        # Check missing book
        if book in szit_data and book not in mek_data:
            discrepancies.append(
                {
                    "book": book,
                    "chapter": None,
                    "verse": None,
                    "source": "mek",
                    "severity": "missing_book",
                    "type": "missing_book",
                    "szit_text": None,
                    "mek_text": None,
                }
            )
            continue

        if book in mek_data and book not in szit_data:
            discrepancies.append(
                {
                    "book": book,
                    "chapter": None,
                    "verse": None,
                    "source": "szit",
                    "severity": "missing_book",
                    "type": "missing_book",
                    "szit_text": None,
                    "mek_text": None,
                }
            )
            continue

        # Book is present in both, check chapters
        szit_chaps = szit_data[book]
        mek_chaps = mek_data[book]
        all_chapters = sorted(list(set(szit_chaps.keys()) | set(mek_chaps.keys())))

        for chapter in all_chapters:
            # Check missing chapter
            if chapter in szit_chaps and chapter not in mek_chaps:
                discrepancies.append(
                    {
                        "book": book,
                        "chapter": chapter,
                        "verse": None,
                        "source": "mek",
                        "severity": "missing_chapter",
                        "type": "missing_chapter",
                        "szit_text": None,
                        "mek_text": None,
                    }
                )
                continue

            if chapter in mek_chaps and chapter not in szit_chaps:
                discrepancies.append(
                    {
                        "book": book,
                        "chapter": chapter,
                        "verse": None,
                        "source": "szit",
                        "severity": "missing_chapter",
                        "type": "missing_chapter",
                        "szit_text": None,
                        "mek_text": None,
                    }
                )
                continue

            # Chapter is present in both, check verses
            szit_verses = szit_chaps[chapter]
            mek_verses = mek_chaps[chapter]
            all_verses = sorted(list(set(szit_verses.keys()) | set(mek_verses.keys())))

            for verse in all_verses:
                # Check missing verse
                if verse in szit_verses and verse not in mek_verses:
                    discrepancies.append(
                        {
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "source": "mek",
                            "severity": "missing_verse",
                            "type": "missing_verse",
                            "szit_text": szit_verses[verse],
                            "mek_text": None,
                        }
                    )
                    continue

                if verse in mek_verses and verse not in szit_verses:
                    discrepancies.append(
                        {
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "source": "szit",
                            "severity": "missing_verse",
                            "type": "missing_verse",
                            "szit_text": None,
                            "mek_text": mek_verses[verse],
                        }
                    )
                    continue

                # Verse is present in both, check text differences
                szit_text = szit_verses[verse]
                mek_text = mek_verses[verse]

                if normalize_and_collapse(szit_text) != normalize_and_collapse(
                    mek_text
                ):
                    discrepancies.append(
                        {
                            "book": book,
                            "chapter": chapter,
                            "verse": verse,
                            "source": "both",
                            "severity": "text_diff",
                            "type": "text_diff",
                            "szit_text": szit_text,
                            "mek_text": mek_text,
                        }
                    )

    return discrepancies
