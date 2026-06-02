"""Tests for VibeVoice alignment module.

Tests both VibeVoice paths:
1. ASR -> word transcripts -> RapidFuzz matching (vibevoice_asr, vibevoice_asr_match)
2. Direct alignment -> verse timestamps (vibevoice_direct)

Uses sys.modules mocking for transformers/torch/soundfile since tests run
without GPU/model.
"""

import sys
from types import ModuleType
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock

# Ensure mock modules exist (test_align.py may have already set them)
_transformers = sys.modules.get("transformers") or ModuleType("transformers")
_torch = sys.modules.get("torch") or ModuleType("torch")
_soundfile = sys.modules.get("soundfile") or ModuleType("soundfile")

sys.modules["transformers"] = _transformers
sys.modules["torch"] = _torch
sys.modules["soundfile"] = _soundfile

from bibliavox.align.vibevoice import (  # noqa: E402
    vibevoice_asr,
    vibevoice_direct,
    vibevoice_asr_match,
)


def _make_mono_audio(samples=16000):
    audio = MagicMock()
    audio.shape = (samples,)
    return audio


def _make_stereo_audio(samples=16000):
    audio = MagicMock()
    audio.shape = (samples, 2)
    mono = MagicMock()
    mono.shape = (samples,)
    audio.mean.return_value = mono
    return audio


def _setup_vibevoice_mocks():
    """Set up standard VibeVoice mocks on sys.modules entries."""
    sf = sys.modules["soundfile"]
    sf.read = lambda path: (_make_mono_audio(16000), 16000)

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
    mock_processor.return_value = mock_inputs
    mock_processor.batch_decode.return_value = [
        {"speaker": "Speaker 0", "start": 0.0, "end": 1.0, "content": "Hello world"},
    ]

    mock_model = MagicMock()
    mock_model.to.return_value = mock_model
    mock_model.generate.return_value = [[0, 1, 2]]

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
        mock_processor, _ = _setup_vibevoice_mocks()
        mock_processor.batch_decode.return_value = []
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert result == []

    def test_vibevoice_asr_handles_plain_text_output(self):
        mock_processor, _ = _setup_vibevoice_mocks()
        mock_processor.batch_decode.return_value = ["Hello world"]
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert len(result) == 2
        assert result[0]["word"] == "Hello"
        assert result[0]["probability"] == 0.5

    def test_vibevoice_asr_result_has_probability(self):
        mock_processor, _ = _setup_vibevoice_mocks()
        mock_processor.batch_decode.return_value = [
            {"speaker": "Speaker 0", "start": 0.0, "end": 0.5, "content": "test"},
        ]
        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")
        assert "probability" in result[0]
        assert result[0]["probability"] == 1.0


class TestVibeVoiceDirect:
    def test_vibevoice_direct_returns_verse_segments(self):
        mock_processor, _ = _setup_vibevoice_mocks()
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
        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "Verse one text"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.5
        assert result[0]["speaker"] == "Speaker 0"

    def test_vibevoice_direct_handles_empty_transcription(self):
        mock_processor, _ = _setup_vibevoice_mocks()
        mock_processor.batch_decode.return_value = []
        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )
        assert result == []

    def test_vibevoice_direct_handles_stereo_audio(self):
        stereo_audio = _make_stereo_audio(16000)
        sf = sys.modules["soundfile"]
        sf.read = lambda path: (stereo_audio, 16000)

        torch = sys.modules["torch"]
        torch.bfloat16 = "bfloat16"

        @contextmanager
        def _no_grad():
            yield

        torch.no_grad = _no_grad

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []

        transformers = sys.modules["transformers"]
        transformers.AutoProcessor = MagicMock()
        transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        transformers.VibeVoiceAsrForConditionalGeneration = MagicMock()
        transformers.VibeVoiceAsrForConditionalGeneration.from_pretrained.return_value = MagicMock()

        result = vibevoice_direct(
            Path("test.wav"), model_path="test/model", device="cpu"
        )
        assert isinstance(result, list)
        stereo_audio.mean.assert_called_once_with(axis=1)


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
        mock_processor, _ = _setup_vibevoice_mocks()
        mock_processor.batch_decode.return_value = []
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
