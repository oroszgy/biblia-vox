"""Tests for VibeVoice alignment module.

Tests both VibeVoice paths:
1. ASR → word transcripts → RapidFuzz matching (vibevoice_asr, vibevoice_asr_match)
2. Direct alignment → verse timestamps (vibevoice_direct)

Uses mocking for transformers pipeline since tests run without GPU/model.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVibeVoiceAsr:
    """Test vibevoice_asr function behavior."""

    @patch("bibliavox.align.vibevoice.pipeline")
    def test_vibevoice_asr_returns_word_transcripts(self, mock_pipeline_cls):
        """vibevoice_asr returns list of word-level transcript dicts."""
        from bibliavox.align.vibevoice import vibevoice_asr

        mock_pipe = MagicMock()
        mock_pipe.return_value = {
            "chunks": [
                {"text": "Hello", "timestamp": (0.0, 0.5)},
                {"text": "world", "timestamp": (0.5, 1.0)},
            ]
        }
        mock_pipeline_cls.return_value = mock_pipe

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["word"] == "Hello"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 0.5
        assert result[1]["word"] == "world"

    @patch("bibliavox.align.vibevoice.pipeline")
    def test_vibevoice_asr_calls_pipeline_with_word_timestamps(self, mock_pipeline_cls):
        """vibevoice_asr configures pipeline with return_timestamps='word'."""
        from bibliavox.align.vibevoice import vibevoice_asr

        mock_pipe = MagicMock()
        mock_pipe.return_value = {"chunks": []}
        mock_pipeline_cls.return_value = mock_pipe

        vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        mock_pipeline_cls.assert_called_once_with(
            "automatic-speech-recognition",
            model="test/model",
            device="cpu",
            return_timestamps="word",
        )

    @patch("bibliavox.align.vibevoice.pipeline")
    def test_vibevoice_asr_handles_empty_result(self, mock_pipeline_cls):
        """vibevoice_asr returns empty list when pipeline returns no chunks."""
        from bibliavox.align.vibevoice import vibevoice_asr

        mock_pipe = MagicMock()
        mock_pipe.return_value = {"chunks": []}
        mock_pipeline_cls.return_value = mock_pipe

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert result == []

    @patch("bibliavox.align.vibevoice.pipeline")
    def test_vibevoice_asr_handles_malformed_chunk(self, mock_pipeline_cls):
        """vibevoice_asr skips chunks with missing or malformed timestamp."""
        from bibliavox.align.vibevoice import vibevoice_asr

        mock_pipe = MagicMock()
        mock_pipe.return_value = {
            "chunks": [
                {"text": "good", "timestamp": (0.0, 0.5)},
                {"text": "bad"},  # missing timestamp
                {"text": "also_bad", "timestamp": "invalid"},
                {"text": "good2", "timestamp": (1.0, 1.5)},
            ]
        }
        mock_pipeline_cls.return_value = mock_pipe

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert len(result) == 2
        assert result[0]["word"] == "good"
        assert result[1]["word"] == "good2"

    @patch("bibliavox.align.vibevoice.pipeline")
    def test_vibevoice_asr_result_has_probability(self, mock_pipeline_cls):
        """vibevoice_asr results include probability field."""
        from bibliavox.align.vibevoice import vibevoice_asr

        mock_pipe = MagicMock()
        mock_pipe.return_value = {
            "chunks": [
                {"text": "test", "timestamp": (0.0, 0.5)},
            ]
        }
        mock_pipeline_cls.return_value = mock_pipe

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert "probability" in result[0]
        assert result[0]["probability"] == 1.0


class TestVibeVoiceDirect:
    """Test vibevoice_direct function behavior."""

    @patch("bibliavox.align.vibevoice.sf")
    @patch("bibliavox.align.vibevoice.torch")
    @patch("bibliavox.align.vibevoice.VibeVoiceForSpeechToText")
    @patch("bibliavox.align.vibevoice.AutoProcessor")
    def test_vibevoice_direct_returns_verse_segments(
        self, mock_processor_cls, mock_model_cls, mock_torch, mock_sf
    ):
        """vibevoice_direct returns list of segment dicts with text, start, end, speaker."""
        from bibliavox.align.vibevoice import vibevoice_direct

        # Mock soundfile
        import numpy as np

        mock_sf.read.return_value = (np.zeros(16000), 16000)

        # Mock processor
        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = [
            {
                "text": "Verse one text",
                "start": 0.0,
                "end": 2.5,
                "speaker": "Speaker 0",
            },
            {
                "text": "Verse two text",
                "start": 2.5,
                "end": 5.0,
                "speaker": "Speaker 0",
            },
        ]
        mock_processor_cls.from_pretrained.return_value = mock_processor

        # Mock model
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        # Mock torch
        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )
        mock_torch.float16 = "float16"

        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "Verse one text"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.5
        assert result[0]["speaker"] == "Speaker 0"

    @patch("bibliavox.align.vibevoice.sf")
    @patch("bibliavox.align.vibevoice.torch")
    @patch("bibliavox.align.vibevoice.VibeVoiceForSpeechToText")
    @patch("bibliavox.align.vibevoice.AutoProcessor")
    def test_vibevoice_direct_uses_parsed_format(
        self, mock_processor_cls, mock_model_cls, mock_torch, mock_sf
    ):
        """vibevoice_direct calls batch_decode with return_format='parsed'."""
        from bibliavox.align.vibevoice import vibevoice_direct

        import numpy as np

        mock_sf.read.return_value = (np.zeros(16000), 16000)

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []
        mock_processor_cls.from_pretrained.return_value = mock_processor

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )
        mock_torch.float16 = "float16"

        vibevoice_direct(Path("test.wav"), model_path="test/model", device="cpu")

        mock_processor.batch_decode.assert_called_once()
        call_kwargs = mock_processor.batch_decode.call_args
        assert call_kwargs[1].get("return_format") == "parsed" or (
            len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "parsed"
        )

    @patch("bibliavox.align.vibevoice.sf")
    @patch("bibliavox.align.vibevoice.torch")
    @patch("bibliavox.align.vibevoice.VibeVoiceForSpeechToText")
    @patch("bibliavox.align.vibevoice.AutoProcessor")
    def test_vibevoice_direct_handles_empty_transcription(
        self, mock_processor_cls, mock_model_cls, mock_torch, mock_sf
    ):
        """vibevoice_direct returns empty list when transcription is empty."""
        from bibliavox.align.vibevoice import vibevoice_direct

        import numpy as np

        mock_sf.read.return_value = (np.zeros(16000), 16000)

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []
        mock_processor_cls.from_pretrained.return_value = mock_processor

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )
        mock_torch.float16 = "float16"

        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )

        assert result == []

    @patch("bibliavox.align.vibevoice.sf")
    @patch("bibliavox.align.vibevoice.torch")
    @patch("bibliavox.align.vibevoice.VibeVoiceForSpeechToText")
    @patch("bibliavox.align.vibevoice.AutoProcessor")
    def test_vibevoice_direct_handles_stereo_audio(
        self, mock_processor_cls, mock_model_cls, mock_torch, mock_sf
    ):
        """vibevoice_direct converts stereo audio to mono."""
        from bibliavox.align.vibevoice import vibevoice_direct

        import numpy as np

        # Stereo audio: shape (16000, 2)
        stereo_audio = np.zeros((16000, 2))
        mock_sf.read.return_value = (stereo_audio, 16000)

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []
        mock_processor_cls.from_pretrained.return_value = mock_processor

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()
        mock_model_cls.from_pretrained.return_value = mock_model

        mock_torch.no_grad.return_value = MagicMock(
            __enter__=MagicMock(), __exit__=MagicMock()
        )
        mock_torch.float16 = "float16"

        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )

        # Should not raise; stereo→mono conversion handles it
        assert isinstance(result, list)


class TestVibeVoiceAsrMatch:
    """Test vibevoice_asr_match function behavior."""

    @patch("bibliavox.align.vibevoice.match_verses")
    @patch("bibliavox.align.vibevoice.vibevoice_asr")
    def test_vibevoice_asr_match_calls_match_verses(self, mock_asr, mock_match):
        """vibevoice_asr_match passes ASR output to match_verses."""
        from bibliavox.align.vibevoice import vibevoice_asr_match

        mock_asr.return_value = [
            {"word": "test", "start": 0.0, "end": 0.5, "probability": 1.0}
        ]
        mock_match.return_value = [
            {
                "verse_id": "1",
                "start_sec": 0.0,
                "end_sec": 0.5,
                "confidence_score": 95.0,
            }
        ]

        verses = [{"verse_id": "1", "text": "test"}]
        result = vibevoice_asr_match(
            Path("test.wav"), verses, model_path="test/model", device="cpu"
        )

        mock_asr.assert_called_once_with(Path("test.wav"), "test/model", "cpu")
        mock_match.assert_called_once_with(verses, mock_asr.return_value)
        assert len(result) == 1
        assert result[0]["verse_id"] == "1"

    @patch("bibliavox.align.vibevoice.match_verses")
    @patch("bibliavox.align.vibevoice.vibevoice_asr")
    def test_vibevoice_asr_match_returns_empty_when_no_words(
        self, mock_asr, mock_match
    ):
        """vibevoice_asr_match returns empty when ASR produces no words."""
        from bibliavox.align.vibevoice import vibevoice_asr_match

        mock_asr.return_value = []
        mock_match.return_value = []

        result = vibevoice_asr_match(
            Path("test.wav"),
            [{"verse_id": "1", "text": "test"}],
            model_path="test/model",
            device="cpu",
        )

        assert result == []

    @patch("bibliavox.align.vibevoice.match_verses")
    @patch("bibliavox.align.vibevoice.vibevoice_asr")
    def test_vibevoice_asr_match_result_has_expected_keys(self, mock_asr, mock_match):
        """vibevoice_asr_match results contain verse_id, start_sec, end_sec, confidence_score."""
        from bibliavox.align.vibevoice import vibevoice_asr_match

        mock_asr.return_value = [
            {"word": "hello", "start": 0.0, "end": 0.5, "probability": 1.0},
            {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.9},
        ]
        mock_match.return_value = [
            {
                "verse_id": "1",
                "start_sec": 0.0,
                "end_sec": 1.0,
                "confidence_score": 88.5,
            }
        ]

        result = vibevoice_asr_match(
            Path("test.wav"),
            [{"verse_id": "1", "text": "hello world"}],
            model_path="test/model",
            device="cpu",
        )

        assert len(result) == 1
        r = result[0]
        assert "verse_id" in r
        assert "start_sec" in r
        assert "end_sec" in r
        assert "confidence_score" in r
