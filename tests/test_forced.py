"""Tests for MMS_FA forced alignment pipeline.

Tests the align_verse, align_chapter, and save_forced_alignment functions.
Uses mocking for GPU/torchaudio operations since tests run on CI without GPU.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAlignVerse:
    """Test align_verse function behavior."""

    @patch("bibliavox.align.forced.torchaudio")
    @patch("bibliavox.align.forced.torch")
    def test_align_verse_returns_words_and_phones(self, mock_torch, mock_torchaudio):
        """align_verse returns dict with words, phones, and text keys."""
        from bibliavox.align.forced import align_verse

        # Setup mock bundle
        mock_bundle = MagicMock()
        mock_bundle.sample_rate = 16000

        # Mock model, tokenizer, aligner
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_aligner = MagicMock()

        mock_bundle.get_model.return_value = mock_model
        mock_bundle.get_tokenizer.return_value = mock_tokenizer
        mock_bundle.get_aligner.return_value = mock_aligner

        # Mock emission output: [batch, time, vocab]
        mock_emission = MagicMock()
        mock_emission.__getitem__ = MagicMock(return_value=MagicMock())
        mock_emission.size.return_value = 100  # time dimension

        mock_model.return_value = (mock_emission, None)

        # Mock tokenizer output (list of token lists)
        mock_tokenizer.return_value = [[1, 2, 3]]

        # Mock token spans
        mock_span1 = MagicMock()
        mock_span1.token = "a"
        mock_span1.start = 0
        mock_span1.end = 10
        mock_span1.score = 0.95

        mock_span2 = MagicMock()
        mock_span2.token = "b"
        mock_span2.start = 10
        mock_span2.end = 20
        mock_span2.score = 0.90

        mock_aligner.return_value = [[mock_span1, mock_span2]]

        # Mock torchaudio.load and resample
        mock_waveform = MagicMock()
        mock_waveform.to.return_value = mock_waveform
        mock_waveform.size.return_value = 160000  # 10 seconds at 16kHz
        mock_torchaudio.load.return_value = (mock_waveform, 16000)
        mock_torchaudio.functional.resample.return_value = mock_waveform

        # Mock torch operations
        mock_torch.inference_mode.return_value.__enter__ = MagicMock()
        mock_torch.inference_mode.return_value.__exit__ = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            result = align_verse(Path(tmp.name), "ab", device="cpu")

        assert "words" in result
        assert "phones" in result
        assert "text" in result
        assert result["text"] == "ab"
        assert isinstance(result["words"], list)
        assert isinstance(result["phones"], list)

    @patch("bibliavox.align.forced.torchaudio")
    @patch("bibliavox.align.forced.torch")
    def test_align_verse_phones_have_correct_keys(self, mock_torch, mock_torchaudio):
        """Phone-level output contains token, start, end, score keys."""
        from bibliavox.align.forced import align_verse

        mock_bundle = MagicMock()
        mock_bundle.sample_rate = 16000
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_aligner = MagicMock()
        mock_bundle.get_model.return_value = mock_model
        mock_bundle.get_tokenizer.return_value = mock_tokenizer
        mock_bundle.get_aligner.return_value = mock_aligner

        mock_emission = MagicMock()
        mock_emission.size.return_value = 100
        mock_model.return_value = (mock_emission, None)
        mock_tokenizer.return_value = [[1]]

        mock_span = MagicMock()
        mock_span.token = "h"
        mock_span.start = 5
        mock_span.end = 15
        mock_span.score = 0.92
        mock_aligner.return_value = [[mock_span]]

        mock_waveform = MagicMock()
        mock_waveform.to.return_value = mock_waveform
        mock_waveform.size.return_value = 160000
        mock_torchaudio.load.return_value = (mock_waveform, 16000)
        mock_torchaudio.functional.resample.return_value = mock_waveform

        mock_torch.inference_mode.return_value.__enter__ = MagicMock()
        mock_torch.inference_mode.return_value.__exit__ = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            result = align_verse(Path(tmp.name), "hello", device="cpu")

        phone = result["phones"][0]
        assert "token" in phone
        assert "start" in phone
        assert "end" in phone
        assert "score" in phone

    @patch("bibliavox.align.forced.torchaudio")
    @patch("bibliavox.align.forced.torch")
    def test_align_verse_words_have_correct_keys(self, mock_torch, mock_torchaudio):
        """Word-level output contains word, start, end, score keys."""
        from bibliavox.align.forced import align_verse

        mock_bundle = MagicMock()
        mock_bundle.sample_rate = 16000
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_aligner = MagicMock()
        mock_bundle.get_model.return_value = mock_model
        mock_bundle.get_tokenizer.return_value = mock_tokenizer
        mock_bundle.get_aligner.return_value = mock_aligner

        mock_emission = MagicMock()
        mock_emission.size.return_value = 100
        mock_model.return_value = (mock_emission, None)

        # Two words: "hello" (5 chars) and "world" (5 chars)
        mock_tokenizer.return_value = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]

        spans_word1 = []
        for i in range(5):
            s = MagicMock()
            s.token = chr(ord("a") + i)
            s.start = i * 2
            s.end = (i + 1) * 2
            s.score = 0.9
            spans_word1.append(s)

        spans_word2 = []
        for i in range(5):
            s = MagicMock()
            s.token = chr(ord("f") + i)
            s.start = 10 + i * 2
            s.end = 10 + (i + 1) * 2
            s.score = 0.85
            spans_word2.append(s)

        mock_aligner.return_value = [spans_word1, spans_word2]

        mock_waveform = MagicMock()
        mock_waveform.to.return_value = mock_waveform
        mock_waveform.size.return_value = 160000
        mock_torchaudio.load.return_value = (mock_waveform, 16000)
        mock_torchaudio.functional.resample.return_value = mock_waveform

        mock_torch.inference_mode.return_value.__enter__ = MagicMock()
        mock_torch.inference_mode.return_value.__exit__ = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            result = align_verse(Path(tmp.name), "hello world", device="cpu")

        assert len(result["words"]) == 2
        word = result["words"][0]
        assert "word" in word
        assert "start" in word
        assert "end" in word
        assert "score" in word

    @patch("bibliavox.align.forced.torchaudio")
    @patch("bibliavox.align.forced.torch")
    def test_align_verse_handles_empty_transcript(self, mock_torch, mock_torchaudio):
        """Function handles empty transcript gracefully (returns empty lists)."""
        from bibliavox.align.forced import align_verse

        mock_bundle = MagicMock()
        mock_bundle.sample_rate = 16000
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_aligner = MagicMock()
        mock_bundle.get_model.return_value = mock_model
        mock_bundle.get_tokenizer.return_value = mock_tokenizer
        mock_bundle.get_aligner.return_value = mock_aligner

        mock_emission = MagicMock()
        mock_emission.size.return_value = 100
        mock_model.return_value = (mock_emission, None)

        # Empty transcript produces empty tokens
        mock_tokenizer.return_value = [[]]
        mock_aligner.return_value = [[]]

        mock_waveform = MagicMock()
        mock_waveform.to.return_value = mock_waveform
        mock_waveform.size.return_value = 160000
        mock_torchaudio.load.return_value = (mock_waveform, 16000)
        mock_torchaudio.functional.resample.return_value = mock_waveform

        mock_torch.inference_mode.return_value.__enter__ = MagicMock()
        mock_torch.inference_mode.return_value.__exit__ = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            result = align_verse(Path(tmp.name), "", device="cpu")

        assert result["words"] == []
        assert result["phones"] == []
        assert result["text"] == ""

    @patch("bibliavox.align.forced.torchaudio")
    @patch("bibliavox.align.forced.torch")
    def test_align_verse_handles_single_word(self, mock_torch, mock_torchaudio):
        """Function handles single-word transcript."""
        from bibliavox.align.forced import align_verse

        mock_bundle = MagicMock()
        mock_bundle.sample_rate = 16000
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_aligner = MagicMock()
        mock_bundle.get_model.return_value = mock_model
        mock_bundle.get_tokenizer.return_value = mock_tokenizer
        mock_bundle.get_aligner.return_value = mock_aligner

        mock_emission = MagicMock()
        mock_emission.size.return_value = 100
        mock_model.return_value = (mock_emission, None)
        mock_tokenizer.return_value = [[1, 2, 3]]

        spans = []
        for i in range(3):
            s = MagicMock()
            s.token = chr(ord("a") + i)
            s.start = i * 5
            s.end = (i + 1) * 5
            s.score = 0.88
            spans.append(s)
        mock_aligner.return_value = [spans]

        mock_waveform = MagicMock()
        mock_waveform.to.return_value = mock_waveform
        mock_waveform.size.return_value = 160000
        mock_torchaudio.load.return_value = (mock_waveform, 16000)
        mock_torchaudio.functional.resample.return_value = mock_waveform

        mock_torch.inference_mode.return_value.__enter__ = MagicMock()
        mock_torch.inference_mode.return_value.__exit__ = MagicMock()

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            result = align_verse(Path(tmp.name), "abc", device="cpu")

        assert len(result["words"]) == 1
        assert result["words"][0]["word"] == "abc"


class TestAlignChapter:
    """Test align_chapter function behavior."""

    @patch("bibliavox.align.forced.align_verse")
    def test_align_chapter_returns_list_of_results(self, mock_align_verse):
        """align_chapter returns list with per-verse results."""
        from bibliavox.align.forced import align_chapter

        mock_align_verse.return_value = {
            "words": [{"word": "test", "start": 0.0, "end": 1.0, "score": 0.9}],
            "phones": [{"token": "t", "start": 0.0, "end": 0.2, "score": 0.9}],
            "text": "test",
        }

        verses = [
            {"verse_id": "1", "text": "test"},
            {"verse_id": "2", "text": "test"},
        ]

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            results = align_chapter(Path(tmp.name), verses, device="cpu")

        assert len(results) == 2
        for r in results:
            assert "verse_id" in r
            assert "words" in r
            assert "phones" in r
            assert "start_sec" in r
            assert "end_sec" in r

    @patch("bibliavox.align.forced.align_verse")
    def test_align_chapter_handles_empty_verses(self, mock_align_verse):
        """align_chapter returns empty list for empty input."""
        from bibliavox.align.forced import align_chapter

        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            results = align_chapter(Path(tmp.name), [], device="cpu")

        assert results == []
        mock_align_verse.assert_not_called()


class TestSaveForcedAlignment:
    """Test save_forced_alignment function behavior."""

    def test_save_creates_verse_and_phones_files(self):
        """save_forced_alignment creates both verse-level and phone-level files."""
        from bibliavox.align.forced import save_forced_alignment

        results = [
            {
                "verse_id": "1",
                "words": [{"word": "test", "start": 0.0, "end": 1.0, "score": 0.9}],
                "phones": [{"token": "t", "start": 0.0, "end": 0.2, "score": 0.9}],
                "start_sec": 0.0,
                "end_sec": 1.0,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            verse_path, phones_path = save_forced_alignment(
                results, output_dir, "GEN", 1
            )

            assert verse_path.exists()
            assert phones_path.exists()
            assert "_phones.json" in phones_path.name

    def test_save_verse_file_contains_expected_structure(self):
        """Verse-level JSON contains verse_id, start_sec, end_sec, words."""
        from bibliavox.align.forced import save_forced_alignment

        results = [
            {
                "verse_id": "1",
                "words": [{"word": "hello", "start": 0.0, "end": 0.5, "score": 0.95}],
                "phones": [
                    {"token": "h", "start": 0.0, "end": 0.1, "score": 0.95},
                    {"token": "e", "start": 0.1, "end": 0.2, "score": 0.93},
                ],
                "start_sec": 0.0,
                "end_sec": 0.5,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            verse_path, phones_path = save_forced_alignment(
                results, Path(tmpdir), "GEN", 1
            )

            with open(verse_path, "r", encoding="utf-8") as f:
                verse_data = json.load(f)

            assert isinstance(verse_data, list)
            assert len(verse_data) == 1
            assert "verse_id" in verse_data[0]
            assert "start_sec" in verse_data[0]
            assert "end_sec" in verse_data[0]
            assert "words" in verse_data[0]

    def test_save_phones_file_contains_phone_data(self):
        """Phone-level JSON contains raw phone timestamps per verse."""
        from bibliavox.align.forced import save_forced_alignment

        results = [
            {
                "verse_id": "1",
                "words": [],
                "phones": [
                    {"token": "h", "start": 0.0, "end": 0.1, "score": 0.95},
                ],
                "start_sec": 0.0,
                "end_sec": 0.1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            verse_path, phones_path = save_forced_alignment(
                results, Path(tmpdir), "GEN", 1
            )

            with open(phones_path, "r", encoding="utf-8") as f:
                phones_data = json.load(f)

            assert isinstance(phones_data, list)
            assert len(phones_data) == 1
            assert "phones" in phones_data[0]
            assert phones_data[0]["phones"][0]["token"] == "h"
