"""Tests for dataset coverage audit logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from bibliavox.coverage import audit_coverage
from bibliavox.reference.books import Book
from bibliavox.reference.schema import BookSchema


def _book(usx: str, *, deuterocanonical: bool = False) -> Book:
    return Book(
        usx_code=usx,
        hungarian_name=usx,
        abbreviation=usx,
        book_number=1,
        testament="OT",
        deuterocanonical=deuterocanonical,
    )


def test_audit_coverage_fails_without_known_gap_allowance(tmp_path: Path) -> None:
    schemas = [BookSchema(usx_code="GEN", chapter_count=2, chapters={1: 1, 2: 1})]
    books = [_book("GEN")]
    mapping = {"Genesis": "GEN"}
    szit_data = {"Genesis": {"1": {"1": "text"}}}

    raw_root = tmp_path / "raw"
    prepared_root = tmp_path / "prepared"
    (raw_root / "GEN").mkdir(parents=True)
    (prepared_root / "GEN").mkdir(parents=True)

    (raw_root / "GEN" / "001.mp3").write_bytes(b"mp3")
    (prepared_root / "GEN" / "001.wav").write_bytes(b"wav")
    (prepared_root / "GEN" / "001.index.json").write_text("{}", encoding="utf-8")
    (prepared_root / "GEN" / "001.meta.json").write_text("{}", encoding="utf-8")

    known_path = tmp_path / "known_gaps.json"
    known_path.write_text(
        json.dumps(
            {
                "text": {"GEN": [2]},
                "audio": {"GEN": [2]},
                "audio_extra": {},
            }
        ),
        encoding="utf-8",
    )

    report = audit_coverage(
        allow_known_source_gaps=False,
        known_gaps_path=known_path,
        raw_audio_root=raw_root,
        prepared_audio_root=prepared_root,
        include_remote_audio=False,
        schemas=schemas,
        books=books,
        mapping=mapping,
        szit_data=szit_data,
    )

    assert report["complete"] is False
    summary = cast(dict[str, object], report["summary"])
    unresolved = cast(dict[str, int], summary["unresolved"])
    assert unresolved["text_missing"] == 1
    assert unresolved["audio_raw_missing"] == 1


def test_audit_coverage_passes_with_known_gap_allowance(tmp_path: Path) -> None:
    schemas = [BookSchema(usx_code="GEN", chapter_count=2, chapters={1: 1, 2: 1})]
    books = [_book("GEN")]
    mapping = {"Genesis": "GEN"}
    szit_data = {"Genesis": {"1": {"1": "text"}}}

    raw_root = tmp_path / "raw"
    prepared_root = tmp_path / "prepared"
    (raw_root / "GEN").mkdir(parents=True)
    (prepared_root / "GEN").mkdir(parents=True)

    (raw_root / "GEN" / "001.mp3").write_bytes(b"mp3")
    (prepared_root / "GEN" / "001.wav").write_bytes(b"wav")
    (prepared_root / "GEN" / "001.index.json").write_text("{}", encoding="utf-8")
    (prepared_root / "GEN" / "001.meta.json").write_text("{}", encoding="utf-8")

    known_path = tmp_path / "known_gaps.json"
    known_path.write_text(
        json.dumps(
            {
                "text": {"GEN": [2]},
                "audio": {"GEN": [2]},
                "audio_extra": {},
            }
        ),
        encoding="utf-8",
    )

    report = audit_coverage(
        allow_known_source_gaps=True,
        known_gaps_path=known_path,
        raw_audio_root=raw_root,
        prepared_audio_root=prepared_root,
        include_remote_audio=False,
        schemas=schemas,
        books=books,
        mapping=mapping,
        szit_data=szit_data,
    )

    assert report["complete"] is True
    summary = cast(dict[str, object], report["summary"])
    unresolved = cast(dict[str, int], summary["unresolved"])
    assert unresolved["text_missing"] == 0
    assert unresolved["audio_raw_missing"] == 0


def test_audit_coverage_deuterocanonical_allowance(tmp_path: Path) -> None:
    schemas = [BookSchema(usx_code="TOB", chapter_count=1, chapters={1: 1})]
    books = [_book("TOB", deuterocanonical=True)]
    mapping = {"Tobit": "TOB"}
    szit_data = {}

    report = audit_coverage(
        allow_deuterocanonical_missing=True,
        allow_known_source_gaps=False,
        known_gaps_path=tmp_path / "none.json",
        raw_audio_root=tmp_path / "raw",
        prepared_audio_root=tmp_path / "prepared",
        include_remote_audio=False,
        schemas=schemas,
        books=books,
        mapping=mapping,
        szit_data=szit_data,
    )

    summary = cast(dict[str, object], report["summary"])
    assert summary["books_scoped"] == 0
    assert report["complete"] is True
