"""Tests for SZIT JSON to JSONL conversion."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from unittest.mock import patch

import pytest

from bibliavox.text.jsonl_converter import convert_to_jsonl


@pytest.fixture()
def sample_szit_data() -> dict:
    """Sample SZIT data with two books, one known and one unknown."""
    return {
        "Genesis": {
            "1": {
                "1": "In the beginning God created the heaven and the earth.",
                "2": "And the earth was without form, and void.",
            },
            "2": {
                "1": "Thus the heavens and the earth were finished.",
            },
        },
        "Exodus": {
            "1": {
                "1": "Now these are the names of the children of Israel.",
            },
        },
        "UnknownBook": {
            "1": {
                "1": "This should be skipped.",
            },
        },
    }


class TestConvertToJsonl:
    """Tests for convert_to_jsonl function."""

    def test_returns_correct_verse_count(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Should return total number of verses written."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            count = convert_to_jsonl(output_path=output)
        # Genesis: 3 verses, Exodus: 1 verse, UnknownBook: skipped
        assert count == 4

    def test_each_line_is_valid_json(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Each line should be valid JSON."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            convert_to_jsonl(output_path=output)

        lines = output.read_text().strip().splitlines()
        assert len(lines) > 0
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

    def test_jsonl_has_correct_keys(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Each record should have book, chapter, verse, text keys."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            convert_to_jsonl(output_path=output)

        for line in output.read_text().strip().splitlines():
            record = json.loads(line)
            assert set(record.keys()) == {"book", "chapter", "verse", "text"}

    def test_book_field_uses_usx_codes(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Book field should use USX codes (e.g., GEN not Genesis)."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            convert_to_jsonl(output_path=output)

        books = set()
        for line in output.read_text().strip().splitlines():
            record = json.loads(line)
            books.add(record["book"])

        assert "GEN" in books
        assert "EXO" in books
        assert "Genesis" not in books
        assert "Exodus" not in books

    def test_text_is_nfc_normalized(
        self,
        tmp_path: Path,
    ) -> None:
        """Text field should be NFC normalized."""
        # Create data with non-NFC text (decomposed form)
        decomposed = "e\u0301"  # é in NFD form
        nfc_form = unicodedata.normalize("NFC", decomposed)
        data = {
            "Genesis": {
                "1": {
                    "1": f"Verse with {decomposed} character.",
                },
            },
        }
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=data,
        ):
            convert_to_jsonl(output_path=output)

        record = json.loads(output.read_text().strip().splitlines()[0])
        assert record["text"] == f"Verse with {nfc_form} character."

    def test_unknown_books_skipped(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Unknown English book names should be skipped."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            count = convert_to_jsonl(output_path=output)

        # UnknownBook has 1 verse — should not be counted
        assert count == 4
        for line in output.read_text().strip().splitlines():
            record = json.loads(line)
            assert record["book"] in ("GEN", "EXO")

    def test_one_line_per_verse(self, tmp_path: Path, sample_szit_data: dict) -> None:
        """Output should have exactly one line per verse, no nesting."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            count = convert_to_jsonl(output_path=output)

        lines = output.read_text().strip().splitlines()
        assert len(lines) == count

    def test_verse_numbers_are_integers(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Verse and chapter numbers should be integers, not strings."""
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            convert_to_jsonl(output_path=output)

        for line in output.read_text().strip().splitlines():
            record = json.loads(line)
            assert isinstance(record["verse"], int)
            assert isinstance(record["chapter"], int)

    def test_creates_output_directory(
        self, tmp_path: Path, sample_szit_data: dict
    ) -> None:
        """Should create parent directories if they don't exist."""
        output = tmp_path / "subdir" / "deep" / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=sample_szit_data,
        ):
            convert_to_jsonl(output_path=output)

        assert output.exists()

    def test_empty_book_data(self, tmp_path: Path) -> None:
        """Should handle empty book data gracefully."""
        data = {"Genesis": {"1": {}}}
        output = tmp_path / "szit.jsonl"
        with patch(
            "bibliavox.text.jsonl_converter.load_szit_json",
            return_value=data,
        ):
            count = convert_to_jsonl(output_path=output)

        assert count == 0
        assert output.exists()
