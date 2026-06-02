"""Tests for the export writer module."""

from __future__ import annotations

import json
from pathlib import Path

from collections.abc import Generator

import pytest

from bibliavox.export.writer import (
    export_chapter_jsonl,
    is_chapter_complete,
    load_canonical_text,
    normalize_confidence,
    reset_canonical_text_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache() -> Generator[None]:
    """Reset canonical text cache between tests."""
    reset_canonical_text_cache()
    yield
    reset_canonical_text_cache()


class TestLoadCanonicalText:
    """Tests for load_canonical_text()."""

    def test_loads_verses_for_book_chapter(self, tmp_path: Path) -> None:
        """Returns list of dicts with book, chapter, verse, text keys."""
        mek_dir = tmp_path / "processed" / "text"
        mek_dir.mkdir(parents=True)
        mek_file = mek_dir / "mek.jsonl"
        lines = [
            json.dumps({"book": "TIT", "chapter": 1, "verse": 1, "text": "Verse one."}),
            json.dumps({"book": "TIT", "chapter": 1, "verse": 2, "text": "Verse two."}),
            json.dumps(
                {"book": "GEN", "chapter": 1, "verse": 1, "text": "In the beginning..."}
            ),
        ]
        mek_file.write_text("\n".join(lines) + "\n")

        result = load_canonical_text(tmp_path)
        # Should return dict mapping (book, chapter, verse) -> text
        assert result[("TIT", 1, "1")] == "Verse one."
        assert result[("TIT", 1, "2")] == "Verse two."
        assert result[("GEN", 1, "1")] == "In the beginning..."

    def test_returns_empty_dict_for_missing_file(self, tmp_path: Path) -> None:
        """Returns empty dict when mek.jsonl does not exist."""
        result = load_canonical_text(tmp_path)
        assert result == {}

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        """Skips empty lines in mek.jsonl."""
        mek_dir = tmp_path / "processed" / "text"
        mek_dir.mkdir(parents=True)
        mek_file = mek_dir / "mek.jsonl"
        mek_file.write_text(
            '{"book": "TIT", "chapter": 1, "verse": 1, "text": "A"}\n\n'
            '{"book": "TIT", "chapter": 1, "verse": 2, "text": "B"}\n'
        )

        result = load_canonical_text(tmp_path)
        assert len(result) == 2


class TestNormalizeConfidence:
    """Tests for normalize_confidence()."""

    def test_normalizes_to_0_1_range(self) -> None:
        """Divides by max to normalize scores to 0-1."""
        scores = [100.0, 50.0, 75.0]
        result = normalize_confidence(scores)
        assert result == [1.0, 0.5, 0.75]

    def test_handles_all_zeros(self) -> None:
        """Returns [0.0, ...] when max is 0."""
        scores = [0.0, 0.0, 0.0]
        result = normalize_confidence(scores)
        assert result == [0.0, 0.0, 0.0]

    def test_handles_empty_list(self) -> None:
        """Returns empty list for empty input."""
        result = normalize_confidence([])
        assert result == []

    def test_single_score(self) -> None:
        """Single score normalizes to 1.0."""
        result = normalize_confidence([42.0])
        assert result == [1.0]


class TestExportChapterJsonl:
    """Tests for export_chapter_jsonl()."""

    def _make_matched_json(
        self,
        tmp_path: Path,
        verses: list[dict],
        chapter: str = "TIT 1",
        model: str = "test/model",
    ) -> Path:
        """Create a minimal matched JSON file."""
        data = {
            "chapter": chapter,
            "model": model,
            "metrics": {"canonical_verses": len(verses), "aligned_verses": len(verses)},
            "verses": verses,
        }
        path = tmp_path / "matched.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def _make_mek_jsonl(self, tmp_path: Path, verses: list[dict]) -> None:
        """Create a minimal mek.jsonl file."""
        mek_dir = tmp_path / "processed" / "text"
        mek_dir.mkdir(parents=True)
        mek_file = mek_dir / "mek.jsonl"
        lines = [json.dumps(v, ensure_ascii=False) for v in verses]
        mek_file.write_text("\n".join(lines) + "\n")

    def test_writes_all_d07_fields(self, tmp_path: Path) -> None:
        """Output contains all 11 D-07 fields per verse."""
        self._make_mek_jsonl(
            tmp_path,
            [
                {"book": "TIT", "chapter": 1, "verse": 1, "text": "Canonical text."},
            ],
        )
        matched = self._make_matched_json(
            tmp_path,
            [
                {
                    "verse_id": "1",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                    "confidence_score": 90.0,
                    "canonical_text": "Canonical text.",
                    "matched_text": "Canonical text.",
                },
            ],
        )

        output_file = tmp_path / "output.jsonl"
        count = export_chapter_jsonl(
            matched, "audio.wav", "SZIT", output_file, tmp_path
        )

        assert count == 1
        row = json.loads(output_file.read_text().strip())
        expected_fields = {
            "verse_ref",
            "audio_file",
            "start_sec",
            "end_sec",
            "source",
            "translation",
            "confidence",
            "canonical_text",
            "matched_text",
            "wer",
            "cer",
        }
        assert set(row.keys()) == expected_fields

    def test_failed_verses_have_null_timestamps(self, tmp_path: Path) -> None:
        """Failed verses (no start_sec/end_sec) appear with null timestamps and 0 confidence."""
        self._make_mek_jsonl(
            tmp_path,
            [
                {"book": "TIT", "chapter": 1, "verse": 1, "text": "Text."},
            ],
        )
        matched = self._make_matched_json(
            tmp_path,
            [
                {
                    "verse_id": "1",
                    "confidence_score": 0,
                    "canonical_text": "Text.",
                    "matched_text": "",
                },
            ],
        )

        output_file = tmp_path / "output.jsonl"
        export_chapter_jsonl(matched, "audio.wav", "SZIT", output_file, tmp_path)

        row = json.loads(output_file.read_text().strip())
        assert row["start_sec"] is None
        assert row["end_sec"] is None
        assert row["confidence"] == 0.0

    def test_computes_wer_cer(self, tmp_path: Path) -> None:
        """WER and CER are computed per verse from canonical vs matched text."""
        self._make_mek_jsonl(
            tmp_path,
            [
                {"book": "TIT", "chapter": 1, "verse": 1, "text": "hello world"},
            ],
        )
        matched = self._make_matched_json(
            tmp_path,
            [
                {
                    "verse_id": "1",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                    "confidence_score": 100.0,
                    "canonical_text": "hello world",
                    "matched_text": "hello word",
                },
            ],
        )

        output_file = tmp_path / "output.jsonl"
        count = export_chapter_jsonl(
            matched, "audio.wav", "SZIT", output_file, tmp_path
        )

        assert count == 1
        row = json.loads(output_file.read_text().strip())
        # "hello world" vs "hello word" — 1 substitution out of 2 words = WER 0.5
        assert row["wer"] == 0.5
        assert row["cer"] > 0.0

    def test_returns_count_of_lines_written(self, tmp_path: Path) -> None:
        """Returns the number of lines written."""
        self._make_mek_jsonl(
            tmp_path,
            [
                {"book": "TIT", "chapter": 1, "verse": 1, "text": "A"},
                {"book": "TIT", "chapter": 1, "verse": 2, "text": "B"},
                {"book": "TIT", "chapter": 1, "verse": 3, "text": "C"},
            ],
        )
        matched = self._make_matched_json(
            tmp_path,
            [
                {
                    "verse_id": "1",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                    "confidence_score": 90.0,
                    "canonical_text": "A",
                    "matched_text": "A",
                },
                {
                    "verse_id": "2",
                    "start_sec": 5.0,
                    "end_sec": 10.0,
                    "confidence_score": 80.0,
                    "canonical_text": "B",
                    "matched_text": "B",
                },
                {
                    "verse_id": "3",
                    "start_sec": 10.0,
                    "end_sec": 15.0,
                    "confidence_score": 70.0,
                    "canonical_text": "C",
                    "matched_text": "C",
                },
            ],
        )

        output_file = tmp_path / "output.jsonl"
        count = export_chapter_jsonl(
            matched, "audio.wav", "SZIT", output_file, tmp_path
        )
        assert count == 3


class TestIsChapterComplete:
    """Tests for is_chapter_complete()."""

    def test_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        """Returns False when export file does not exist."""
        export_path = tmp_path / "nonexistent.jsonl"
        assert is_chapter_complete(export_path, "test/model") is False

    def test_returns_true_when_all_verses_complete(self, tmp_path: Path) -> None:
        """Returns True when all verses for model have non-null timestamps."""
        export_path = tmp_path / "export.jsonl"
        lines = [
            json.dumps(
                {
                    "verse_ref": "TIT 1:1",
                    "source": "test/model",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                }
            ),
            json.dumps(
                {
                    "verse_ref": "TIT 1:2",
                    "source": "test/model",
                    "start_sec": 5.0,
                    "end_sec": 10.0,
                }
            ),
        ]
        export_path.write_text("\n".join(lines) + "\n")
        assert is_chapter_complete(export_path, "test/model") is True

    def test_returns_false_when_any_verse_has_null_timestamp(
        self, tmp_path: Path
    ) -> None:
        """Returns False when any verse has null start_sec or end_sec."""
        export_path = tmp_path / "export.jsonl"
        lines = [
            json.dumps(
                {
                    "verse_ref": "TIT 1:1",
                    "source": "test/model",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                }
            ),
            json.dumps(
                {
                    "verse_ref": "TIT 1:2",
                    "source": "test/model",
                    "start_sec": None,
                    "end_sec": None,
                }
            ),
        ]
        export_path.write_text("\n".join(lines) + "\n")
        assert is_chapter_complete(export_path, "test/model") is False

    def test_ignores_other_models(self, tmp_path: Path) -> None:
        """Only checks verses matching the given model."""
        export_path = tmp_path / "export.jsonl"
        lines = [
            json.dumps(
                {
                    "verse_ref": "TIT 1:1",
                    "source": "model/a",
                    "start_sec": 1.0,
                    "end_sec": 5.0,
                }
            ),
            json.dumps(
                {
                    "verse_ref": "TIT 1:1",
                    "source": "model/b",
                    "start_sec": None,
                    "end_sec": None,
                }
            ),
        ]
        export_path.write_text("\n".join(lines) + "\n")
        assert is_chapter_complete(export_path, "model/a") is True
        assert is_chapter_complete(export_path, "model/b") is False
