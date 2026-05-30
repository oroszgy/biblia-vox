"""Tests for cross-corpora comparison engine."""

from __future__ import annotations

import json
from pathlib import Path

from bibliavox.text.cross_validator import cross_validate_corpora


def write_jsonl(path: Path, lines: list[dict]) -> None:
    """Helper to write records to a JSONL file."""
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def test_cross_validate_matching(tmp_path: Path) -> None:
    """Should return no discrepancies when corpora match perfectly."""
    szit_lines = [
        {
            "book": "GEN",
            "chapter": 1,
            "verse": 1,
            "text": "Kezdetben teremtette Isten az eget és a földet.",
        },
        {
            "book": "GEN",
            "chapter": 1,
            "verse": 2,
            "text": "A föld puszta és üres volt.",
        },
    ]
    mek_lines = [
        {
            "book": "GEN",
            "chapter": 1,
            "verse": 1,
            "text": "Kezdetben teremtette Isten az eget és a földet.",
        },
        {
            "book": "GEN",
            "chapter": 1,
            "verse": 2,
            "text": "A föld puszta és üres volt.",
        },
    ]

    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"
    write_jsonl(szit_path, szit_lines)
    write_jsonl(mek_path, mek_lines)

    discrepancies = cross_validate_corpora(szit_path, mek_path)
    assert discrepancies == []


def test_cross_validate_missing_book(tmp_path: Path) -> None:
    """Should report missing books gracefully."""
    # SZIT has GEN, MEK has EXO (both miss each other's book)
    szit_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "In the beginning"},
    ]
    mek_lines = [
        {"book": "EXO", "chapter": 1, "verse": 1, "text": "These are the names"},
    ]

    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"
    write_jsonl(szit_path, szit_lines)
    write_jsonl(mek_path, mek_lines)

    discrepancies = cross_validate_corpora(szit_path, mek_path)

    # We expect 2 missing book discrepancies
    assert len(discrepancies) == 2

    # GEN missing in MEK
    gen_disc = [d for d in discrepancies if d["book"] == "GEN"][0]
    assert gen_disc["chapter"] is None
    assert gen_disc["verse"] is None
    assert gen_disc["source"] == "mek"
    assert gen_disc["severity"] == "missing_book"
    assert gen_disc["type"] == "missing_book"

    # EXO missing in SZIT
    exo_disc = [d for d in discrepancies if d["book"] == "EXO"][0]
    assert exo_disc["chapter"] is None
    assert exo_disc["verse"] is None
    assert exo_disc["source"] == "szit"
    assert exo_disc["severity"] == "missing_book"
    assert exo_disc["type"] == "missing_book"


def test_cross_validate_missing_chapter(tmp_path: Path) -> None:
    """Should report missing chapters when books are present in both."""
    szit_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "GEN 1:1"},
        {"book": "GEN", "chapter": 2, "verse": 1, "text": "GEN 2:1"},
    ]
    mek_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "GEN 1:1"},
    ]

    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"
    write_jsonl(szit_path, szit_lines)
    write_jsonl(mek_path, mek_lines)

    discrepancies = cross_validate_corpora(szit_path, mek_path)

    assert len(discrepancies) == 1
    disc = discrepancies[0]
    assert disc["book"] == "GEN"
    assert disc["chapter"] == 2
    assert disc["verse"] is None
    assert disc["source"] == "mek"
    assert disc["severity"] == "missing_chapter"
    assert disc["type"] == "missing_chapter"


def test_cross_validate_missing_verse(tmp_path: Path) -> None:
    """Should report missing verses when chapters are present in both."""
    szit_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "GEN 1:1"},
        {"book": "GEN", "chapter": 1, "verse": 2, "text": "GEN 1:2"},
    ]
    mek_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "GEN 1:1"},
    ]

    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"
    write_jsonl(szit_path, szit_lines)
    write_jsonl(mek_path, mek_lines)

    discrepancies = cross_validate_corpora(szit_path, mek_path)

    assert len(discrepancies) == 1
    disc = discrepancies[0]
    assert disc["book"] == "GEN"
    assert disc["chapter"] == 1
    assert disc["verse"] == 2
    assert disc["source"] == "mek"
    assert disc["severity"] == "missing_verse"
    assert disc["type"] == "missing_verse"
    assert disc["szit_text"] == "GEN 1:2"
    assert disc["mek_text"] is None


def test_cross_validate_text_diff(tmp_path: Path) -> None:
    """Should report text differences and ignore minor whitespace variations."""
    szit_lines = [
        # Whitespace variations (should NOT trigger text diff)
        {
            "book": "GEN",
            "chapter": 1,
            "verse": 1,
            "text": "Kezdetben   teremtette  Isten",
        },
        # Real text differences (should trigger text diff)
        {"book": "GEN", "chapter": 1, "verse": 2, "text": "A föld puszta volt."},
    ]
    mek_lines = [
        {"book": "GEN", "chapter": 1, "verse": 1, "text": "Kezdetben teremtette Isten"},
        {"book": "GEN", "chapter": 1, "verse": 2, "text": "A föld üres volt."},
    ]

    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"
    write_jsonl(szit_path, szit_lines)
    write_jsonl(mek_path, mek_lines)

    discrepancies = cross_validate_corpora(szit_path, mek_path)

    assert len(discrepancies) == 1
    disc = discrepancies[0]
    assert disc["book"] == "GEN"
    assert disc["chapter"] == 1
    assert disc["verse"] == 2
    assert disc["source"] == "both"
    assert disc["severity"] == "text_diff"
    assert disc["type"] == "text_diff"
    assert disc["szit_text"] == "A föld puszta volt."
    assert disc["mek_text"] == "A föld üres volt."


def test_cross_validate_handles_invalid_json(tmp_path: Path) -> None:
    """Should skip invalid JSON lines without crashing."""
    szit_path = tmp_path / "szit.jsonl"
    mek_path = tmp_path / "mek.jsonl"

    # Write a bad line in MEK
    with open(szit_path, "w", encoding="utf-8") as f:
        f.write('{"book": "GEN", "chapter": 1, "verse": 1, "text": "OK"}\n')
    with open(mek_path, "w", encoding="utf-8") as f:
        f.write("{\n")  # Invalid JSON
        f.write('{"book": "GEN", "chapter": 1, "verse": 1, "text": "OK"}\n')

    discrepancies = cross_validate_corpora(szit_path, mek_path)
    # The valid lines matched, invalid line was skipped safely, so no discrepancies.
    assert discrepancies == []
