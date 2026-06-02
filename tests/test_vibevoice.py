"""Tests for VibeVoice alignment module.

Tests both VibeVoice paths:
1. ASR -> word transcripts -> RapidFuzz matching (vibevoice_asr, vibevoice_asr_match)
2. Direct alignment -> verse timestamps (vibevoice_direct)

Uses sys.modules mocking for transformers/torch/soundfile since tests run
without GPU/model. Uses setdefault to avoid clobbering other test modules' mocks.
"""

import sys
from types import ModuleType

# Mock the heavy modules so tests can run without them installed locally.
# Use setdefault so we don't overwrite mocks set by other test modules (e.g. test_align.py).
sys.modules.setdefault("transformers", ModuleType("transformers"))
sys.modules.setdefault("torch", ModuleType("torch"))
sys.modules.setdefault("soundfile", ModuleType("soundfile"))

mock_transformers = sys.modules["transformers"]
mock_torch = sys.modules["torch"]
mock_soundfile = sys.modules["soundfile"]

from pathlib import Path  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from bibliavox.align.vibevoice import (  # noqa: E402
    vibevoice_asr,
    vibevoice_direct,
    vibevoice_asr_match,
)


def _make_mono_audio(samples=16000):
    """Create a mock mono audio array with shape attribute."""
    audio = MagicMock()
    audio.shape = (samples,)
    return audio


def _make_stereo_audio(samples=16000):
    """Create a mock stereo audio array with shape attribute."""
    audio = MagicMock()
    audio.shape = (samples, 2)
    # mean(axis=1) returns mono
    mono = MagicMock()
    mono.shape = (samples,)
    audio.mean.return_value = mono
    return audio


class TestVibeVoiceAsr:
    """Test vibevoice_asr function behavior."""

    def test_vibevoice_asr_returns_word_transcripts(self):
        """vibevoice_asr returns list of word-level transcript dicts."""

        def fake_pipeline(task, model, device, return_timestamps):
            assert task == "automatic-speech-recognition"
            assert return_timestamps == "word"

            def run(audio_path):
                return {
                    "chunks": [
                        {"text": "Hello", "timestamp": (0.0, 0.5)},
                        {"text": "world", "timestamp": (0.5, 1.0)},
                    ]
                }

            return run

        mock_transformers.pipeline = fake_pipeline

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["word"] == "Hello"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 0.5
        assert result[1]["word"] == "world"

    def test_vibevoice_asr_calls_pipeline_with_word_timestamps(self):
        """vibevoice_asr configures pipeline with return_timestamps='word'."""
        called_with = {}

        def fake_pipeline(task, model, device, return_timestamps):
            called_with["task"] = task
            called_with["model"] = model
            called_with["device"] = device
            called_with["return_timestamps"] = return_timestamps

            def run(audio_path):
                return {"chunks": []}

            return run

        mock_transformers.pipeline = fake_pipeline

        vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert called_with["task"] == "automatic-speech-recognition"
        assert called_with["model"] == "test/model"
        assert called_with["device"] == "cpu"
        assert called_with["return_timestamps"] == "word"

    def test_vibevoice_asr_handles_empty_result(self):
        """vibevoice_asr returns empty list when pipeline returns no chunks."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {"chunks": []}

            return run

        mock_transformers.pipeline = fake_pipeline

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert result == []

    def test_vibevoice_asr_handles_malformed_chunk(self):
        """vibevoice_asr skips chunks with missing or malformed timestamp."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {
                    "chunks": [
                        {"text": "good", "timestamp": (0.0, 0.5)},
                        {"text": "bad"},  # missing timestamp
                        {"text": "also_bad", "timestamp": "invalid"},
                        {"text": "good2", "timestamp": (1.0, 1.5)},
                    ]
                }

            return run

        mock_transformers.pipeline = fake_pipeline

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert len(result) == 2
        assert result[0]["word"] == "good"
        assert result[1]["word"] == "good2"

    def test_vibevoice_asr_result_has_probability(self):
        """vibevoice_asr results include probability field."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {
                    "chunks": [
                        {"text": "test", "timestamp": (0.0, 0.5)},
                    ]
                }

            return run

        mock_transformers.pipeline = fake_pipeline

        result = vibevoice_asr(Path("test.wav"), model_path="test/model", device="cpu")

        assert "probability" in result[0]
        assert result[0]["probability"] == 1.0


class TestVibeVoiceDirect:
    """Test vibevoice_direct function behavior."""

    def test_vibevoice_direct_returns_verse_segments(self):
        """vibevoice_direct returns list of segment dicts with text, start, end, speaker."""
        # Mock soundfile.read to return mono audio
        mock_soundfile.read = lambda path: (_make_mono_audio(16000), 16000)

        # Mock torch
        mock_torch.float16 = "float16"
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock()
        mock_torch.no_grad = lambda: mock_ctx

        # Mock processor
        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = [
            {"text": "Verse one text", "start": 0.0, "end": 2.5, "speaker": "Speaker 0"},
            {"text": "Verse two text", "start": 2.5, "end": 5.0, "speaker": "Speaker 0"},
        ]

        # Mock model
        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()

        mock_transformers.AutoProcessor = MagicMock()
        mock_transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        mock_transformers.VibeVoiceForSpeechToText = MagicMock()
        mock_transformers.VibeVoiceForSpeechToText.from_pretrained.return_value = mock_model

        result = vibevoice_direct(Path("test.wav"), model_path="test/model", device="cpu")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "Verse one text"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.5
        assert result[0]["speaker"] == "Speaker 0"

    def test_vibevoice_direct_uses_parsed_format(self):
        """vibevoice_direct calls batch_decode with return_format='parsed'."""
        mock_soundfile.read = lambda path: (_make_mono_audio(16000), 16000)

        mock_torch.float16 = "float16"
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock()
        mock_torch.no_grad = lambda: mock_ctx

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()

        mock_transformers.AutoProcessor = MagicMock()
        mock_transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        mock_transformers.VibeVoiceForSpeechToText = MagicMock()
        mock_transformers.VibeVoiceForSpeechToText.from_pretrained.return_value = mock_model

        vibevoice_direct(Path("test.wav"), model_path="test/model", device="cpu")

        mock_processor.batch_decode.assert_called_once()
        call_args = mock_processor.batch_decode.call_args
        # Check return_format="parsed" in kwargs or positional args
        assert call_args[1].get("return_format") == "parsed" or (
            len(call_args[0]) > 1 and call_args[0][1] == "parsed"
        )

    def test_vibevoice_direct_handles_empty_transcription(self):
        """vibevoice_direct returns empty list when transcription is empty."""
        mock_soundfile.read = lambda path: (_make_mono_audio(16000), 16000)

        mock_torch.float16 = "float16"
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock()
        mock_torch.no_grad = lambda: mock_ctx

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()

        mock_transformers.AutoProcessor = MagicMock()
        mock_transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        mock_transformers.VibeVoiceForSpeechToText = MagicMock()
        mock_transformers.VibeVoiceForSpeechToText.from_pretrained.return_value = mock_model

        result = vibevoice_direct(Path("test.wav"), model_path="test/model", device="cpu")

        assert result == []

    def test_vibevoice_direct_handles_stereo_audio(self):
        """vibevoice_direct converts stereo audio to mono."""
        # Stereo audio: shape (16000, 2)
        stereo_audio = _make_stereo_audio(16000)
        mock_soundfile.read = lambda path: (stereo_audio, 16000)

        mock_torch.float16 = "float16"
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock()
        mock_torch.no_grad = lambda: mock_ctx

        mock_processor = MagicMock()
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_processor.return_value = mock_inputs
        mock_processor.batch_decode.return_value = []

        mock_model = MagicMock()
        mock_model.to.return_value = mock_model
        mock_model.generate.return_value = MagicMock()

        mock_transformers.AutoProcessor = MagicMock()
        mock_transformers.AutoProcessor.from_pretrained.return_value = mock_processor
        mock_transformers.VibeVoiceForSpeechToText = MagicMock()
        mock_transformers.VibeVoiceForSpeechToText.from_pretrained.return_value = mock_model

        result = vibevoice_direct(Path("test.wav"), model_path="test/model", device="cpu")

        # Should not raise; stereo->mono conversion handles it
        assert isinstance(result, list)
        # Verify mean was called for stereo->mono conversion
        stereo_audio.mean.assert_called_once_with(axis=1)


class TestVibeVoiceAsrMatch:
    """Test vibevoice_asr_match function behavior."""

    def test_vibevoice_asr_match_with_matching_text(self):
        """vibevoice_asr_match produces verse-level results when ASR matches text."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {
                    "chunks": [
                        {"text": "hello", "timestamp": (0.0, 0.5)},
                        {"text": "world", "timestamp": (0.5, 1.0)},
                    ]
                }

            return run

        mock_transformers.pipeline = fake_pipeline

        verses = [{"verse_id": "1", "text": "hello world"}]
        result = vibevoice_asr_match(
            Path("test.wav"), verses, model_path="test/model", device="cpu"
        )

        # Should get a match since ASR output matches verse text
        assert len(result) == 1
        assert result[0]["verse_id"] == "1"
        assert result[0]["start_sec"] == 0.0
        assert result[0]["end_sec"] == 1.0

    def test_vibevoice_asr_match_returns_list(self):
        """vibevoice_asr_match returns a list (possibly empty if no match)."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {"chunks": []}

            return run

        mock_transformers.pipeline = fake_pipeline

        result = vibevoice_asr_match(
            Path("test.wav"),
            [{"verse_id": "1", "text": "test"}],
            model_path="test/model",
            device="cpu",
        )

        assert isinstance(result, list)

    def test_vibevoice_asr_match_result_has_expected_keys(self):
        """vibevoice_asr_match results contain verse_id, start_sec, end_sec, confidence_score."""

        def fake_pipeline(task, model, device, return_timestamps):
            def run(audio_path):
                return {
                    "chunks": [
                        {"text": "hello", "timestamp": (0.0, 0.5)},
                        {"text": "world", "timestamp": (0.5, 1.0)},
                    ]
                }

            return run

        mock_transformers.pipeline = fake_pipeline

        verses = [{"verse_id": "1", "text": "hello world"}]
        result = vibevoice_asr_match(
            Path("test.wav"), verses, model_path="test/model", device="cpu"
        )

        assert len(result) == 1
        r = result[0]
        assert "verse_id" in r
        assert "start_sec" in r
        assert "end_sec" in r
        assert "confidence_score" in r
