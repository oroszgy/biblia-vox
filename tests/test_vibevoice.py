"""Tests for VibeVoice alignment module.

Tests both VibeVoice paths:
1. ASR -> word transcripts -> RapidFuzz matching (vibevoice_asr, vibevoice_asr_match)
2. Direct alignment -> verse timestamps (vibevoice_direct)

Uses sys.modules mocking for transformers/torch since tests run without GPU/model.
"""

import sys
from types import ModuleType
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

# Ensure mock modules exist (test_align.py may have already set them)
_transformers = sys.modules.get("transformers") or ModuleType("transformers")
_torch = sys.modules.get("torch") or ModuleType("torch")

sys.modules["transformers"] = _transformers
sys.modules["torch"] = _torch

from bibliavox.align.vibevoice import (  # noqa: E402
    vibevoice_asr,
    vibevoice_direct,
    vibevoice_asr_match,
)


def _setup_vibevoice_mocks(decode_return=None):
    """Set up standard VibeVoice mocks on sys.modules entries.

    Args:
        decode_return: Return value for processor.decode(). Defaults to a
            parsed list with one segment.
    """
    if decode_return is None:
        decode_return = [
            {"Speaker": 0, "Start": 0.0, "End": 1.0, "Content": "Hello world"},
        ]

    torch = sys.modules["torch"]
    torch.bfloat16 = "bfloat16"

    @contextmanager
    def _no_grad():
        yield

    torch.no_grad = _no_grad

    transformers = sys.modules["transformers"]

    mock_processor = MagicMock()
    mock_inputs = MagicMock()
    mock_inputs.to.return_value = mock_inputs
    mock_inputs.__getitem__ = MagicMock(return_value=MagicMock(shape=[1, 10]))
    mock_processor.apply_transcription_request.return_value = mock_inputs
    mock_processor.decode.return_value = [decode_return]

    mock_model = MagicMock()
    mock_model.to.return_value = mock_model

    # generate() return value must support 2D tensor slicing: output_ids[:, n:]
    mock_output_ids = MagicMock()
    mock_slice = MagicMock()
    mock_output_ids.__getitem__ = MagicMock(return_value=mock_slice)
    mock_model.generate.return_value = mock_output_ids

    transformers.AutoProcessor = MagicMock()
    transformers.AutoProcessor.from_pretrained.return_value = mock_processor
    transformers.VibeVoiceAsrForConditionalGeneration = MagicMock()
    transformers.VibeVoiceAsrForConditionalGeneration.from_pretrained.return_value = (
        mock_model
    )

    return mock_processor, mock_model


class TestVibeVoiceAsr:
    def test_vibevoice_asr_returns_word_transcripts(self):
        _setup_vibevoice_mocks()
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["word"] == "Hello"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 0.5

    def test_vibevoice_asr_handles_empty_result(self):
        _setup_vibevoice_mocks(decode_return=[])
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert result == []

    def test_vibevoice_asr_handles_plain_text_output(self):
        _setup_vibevoice_mocks(decode_return=["Hello world"])
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert len(result) == 2
        assert result[0]["word"] == "Hello"
        assert result[0]["probability"] == 0.5

    def test_vibevoice_asr_result_has_probability(self):
        _setup_vibevoice_mocks()
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert "probability" in result[0]
        assert result[0]["probability"] == 1.0


class TestVibeVoiceDirect:
    def test_vibevoice_direct_returns_verse_segments(self):
        _setup_vibevoice_mocks(
            decode_return=[
                {"Content": "Verse one text", "Start": 0.0, "End": 2.5, "Speaker": 0},
                {"Content": "Verse two text", "Start": 2.5, "End": 5.0, "Speaker": 0},
            ]
        )
        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "Verse one text"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.5
        assert result[0]["speaker"] == "0"

    def test_vibevoice_direct_handles_empty_transcription(self):
        _setup_vibevoice_mocks(decode_return=[])
        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )
        assert result == []


class TestVibeVoiceAsrMatch:
    def test_vibevoice_asr_match_with_matching_text(self):
        _setup_vibevoice_mocks()
        verses = [{"verse_id": "1", "text": "Hello world"}]
        result = vibevoice_asr_match(
            Path("test.wav"), verses, model_path="test/model", device="cpu"
        )
        assert len(result) == 1
        assert result[0]["verse_id"] == "1"
        assert result[0]["start_sec"] == 0.0
        assert result[0]["end_sec"] == 1.0

    def test_vibevoice_asr_match_returns_list(self):
        _setup_vibevoice_mocks(decode_return=[])
        result = vibevoice_asr_match(
            Path("test.wav"),
            [{"verse_id": "1", "text": "test"}],
            model_path="test/model",
            device="cpu",
        )
        assert isinstance(result, list)

    def test_vibevoice_asr_match_result_has_expected_keys(self):
        _setup_vibevoice_mocks()
        verses = [{"verse_id": "1", "text": "Hello world"}]
        result = vibevoice_asr_match(
            Path("test.wav"), verses, model_path="test/model", device="cpu"
        )
        assert len(result) == 1
        r = result[0]
        assert "verse_id" in r
        assert "start_sec" in r
        assert "end_sec" in r
        assert "confidence_score" in r
