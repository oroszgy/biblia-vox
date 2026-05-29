"""Tests for verse marker detection and splitting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bibliavox.text.splitter import VerseMarker, detect_markers, fix_verses


class TestDetectMarkers:
    """Tests for detect_markers function."""

    def test_finds_n_pattern(self) -> None:
        """Should find N) pattern like '2)' in text."""
        text = "(Dávid zsoltára.) 2) Mennyien sokan mondják"
        markers = detect_markers(text)
        assert len(markers) == 1
        assert markers[0].pattern_type == "N)"
        assert markers[0].target_verse == 2
        assert markers[0].raw_match == "2)"

    def test_finds_dd_pattern(self) -> None:
        """Should find ((N)) pattern like '((54))' in text."""
        text = "Text before ((54)) text after"
        markers = detect_markers(text)
        assert len(markers) == 1
        assert markers[0].pattern_type == "((N))"
        assert markers[0].target_verse == 54
        assert markers[0].raw_match == "((54))"

    def test_finds_pn_pattern(self) -> None:
        """Should find (N)N pattern like '(6)7' in text."""
        text = "Text before (6)7 text after"
        markers = detect_markers(text)
        assert len(markers) == 1
        assert markers[0].pattern_type == "(N)N"
        assert markers[0].target_verse == 6
        assert markers[0].raw_match == "(6)7"

    def test_returns_empty_for_no_markers(self) -> None:
        """Should return empty list for text without markers."""
        text = "This is normal verse text without any markers."
        markers = detect_markers(text)
        assert markers == []

    def test_returns_markers_sorted_by_position(self) -> None:
        """Markers should be sorted by their position in text."""
        text = "First 3) then ((10)) and finally (5)6"
        markers = detect_markers(text)
        assert len(markers) == 3
        # Positions should be monotonically increasing
        for i in range(len(markers) - 1):
            assert markers[i].position <= markers[i + 1].position

    def test_marker_position_is_correct(self) -> None:
        """Marker position should point to the start of the match."""
        text = "abc 2) def"
        markers = detect_markers(text)
        assert markers[0].position == 4  # "2)" starts at index 4

    def test_multiple_markers_in_text(self) -> None:
        """Should detect multiple markers of different types."""
        text = "First 2) then ((54)) and (6)7"
        markers = detect_markers(text)
        assert len(markers) == 3
        types = {m.pattern_type for m in markers}
        assert types == {"N)", "((N))", "(N)N"}


class TestFixVerses:
    """Tests for fix_verses function."""

    @pytest.fixture()
    def sample_jsonl(self, tmp_path: Path) -> Path:
        """Create a sample JSONL file with various marker scenarios."""
        records = [
            # Normal verse — should be unchanged
            {
                "book": "GEN",
                "chapter": 1,
                "verse": 1,
                "text": "In the beginning God created.",
            },
            # Psalms: verse 1 with "2)" marker, verse 2 exists → strip marker
            {
                "book": "PSA",
                "chapter": 3,
                "verse": 1,
                "text": "(Dávid zsoltára.) 2) Mennyien sokan mondják",
            },
            {
                "book": "PSA",
                "chapter": 3,
                "verse": 2,
                "text": "Sokan mondják lelkemnek.",
            },
            # 1Ki 22:52: verse 52 with "((54))" marker, verse 54 doesn't exist → split
            {
                "book": "1KI",
                "chapter": 22,
                "verse": 52,
                "text": "Text before ((54)) text after",
            },
            {"book": "1KI", "chapter": 22, "verse": 53, "text": "Existing verse 53."},
            # 2Ki 11:6: verse 6 with "(6)7" marker, verse 7 doesn't exist → split
            {
                "book": "2KI",
                "chapter": 11,
                "verse": 6,
                "text": "Text before (6)7 text after",
            },
        ]
        input_path = tmp_path / "szit.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return input_path

    def test_unchanged_verses_pass_through(
        self, sample_jsonl: Path, tmp_path: Path
    ) -> None:
        """Verses without markers should pass through unchanged."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        records = _load_jsonl(output)
        gen_verses = [r for r in records if r["book"] == "GEN"]
        assert len(gen_verses) == 1
        assert gen_verses[0]["text"] == "In the beginning God created."

    def test_psalms_marker_stripped(self, sample_jsonl: Path, tmp_path: Path) -> None:
        """Psalms superscription markers should be stripped, not split."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        records = _load_jsonl(output)
        psa_verses = sorted(
            [r for r in records if r["book"] == "PSA"],
            key=lambda r: r["verse"],
        )
        # Should still have 2 verses for PSA 3
        assert len(psa_verses) == 2
        # Verse 1 should have "2)" stripped
        assert "2)" not in psa_verses[0]["text"]
        assert "Mennyien" in psa_verses[0]["text"]

    def test_split_creates_new_verse(self, sample_jsonl: Path, tmp_path: Path) -> None:
        """When target verse doesn't exist, should split and create new verse."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        records = _load_jsonl(output)
        ki_verses = sorted(
            [r for r in records if r["book"] == "1KI" and r["chapter"] == 22],
            key=lambda r: r["verse"],
        )
        # Original 52, 53 + new verse from split
        assert len(ki_verses) == 3
        # Check that the split text is present
        texts = {r["verse"]: r["text"] for r in ki_verses}
        assert "Text before" in texts.get(52, "")
        assert "text after" in texts.get(54, "")

    def test_verses_renumbered_sequentially(
        self, sample_jsonl: Path, tmp_path: Path
    ) -> None:
        """After splitting, verses should be re-numbered sequentially."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        records = _load_jsonl(output)
        ki_verses = sorted(
            [r for r in records if r["book"] == "1KI" and r["chapter"] == 22],
            key=lambda r: r["verse"],
        )
        # Verses should be 1, 2, 3 (renumbered)
        verse_nums = [r["verse"] for r in ki_verses]
        assert verse_nums == [1, 2, 3]

    def test_returns_stats_dict(self, sample_jsonl: Path, tmp_path: Path) -> None:
        """Should return stats dict with cleaned/split/unchanged counts."""
        output = tmp_path / "output.jsonl"
        stats = fix_verses(sample_jsonl, output)

        assert "cleaned" in stats
        assert "split" in stats
        assert "unchanged" in stats
        assert stats["cleaned"] >= 1  # PSA 3:1
        assert stats["split"] >= 2  # 1Ki 22:52, 2Ki 11:6
        assert stats["unchanged"] >= 1  # GEN 1:1

    def test_pn_pattern_split(self, sample_jsonl: Path, tmp_path: Path) -> None:
        """(N)N pattern should split correctly when target verse missing."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        records = _load_jsonl(output)
        ki_verses = [r for r in records if r["book"] == "2KI" and r["chapter"] == 11]
        # Should have original verse + split verse
        assert len(ki_verses) >= 2

    def test_output_is_valid_jsonl(self, sample_jsonl: Path, tmp_path: Path) -> None:
        """Output file should contain valid JSONL."""
        output = tmp_path / "output.jsonl"
        fix_verses(sample_jsonl, output)

        for line in output.read_text().strip().splitlines():
            record = json.loads(line)
            assert isinstance(record, dict)
            assert "book" in record
            assert "chapter" in record
            assert "verse" in record
            assert "text" in record


def _load_jsonl(path: Path) -> list[dict]:
    """Load all records from a JSONL file."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records
