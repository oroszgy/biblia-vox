"""Tests for OpenAI Whisper API evaluation module."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestEvaluateWhisperApi:
    """Test suite for evaluate_whisper_api function."""

    def test_returns_dict_with_expected_keys(self, tmp_path: Path) -> None:
        """evaluate_whisper_api returns dict with words, text, cost_usd, duration_sec, error."""
        from bibliavox.align.api_eval import evaluate_whisper_api

        # Create a minimal WAV file (1 second, 16kHz, mono, 16-bit)
        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=1.0)

        mock_response = MagicMock()
        mock_response.text = "Hello world"
        word1 = MagicMock()
        word1.word = "Hello"
        word1.start = 0.0
        word1.end = 0.5
        word2 = MagicMock()
        word2.word = "world"
        word2.start = 0.5
        word2.end = 1.0
        mock_response.words = [word1, word2]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            result = evaluate_whisper_api(wav_path, api_key="test-key")

        assert "words" in result
        assert "text" in result
        assert "cost_usd" in result
        assert "duration_sec" in result
        assert "error" in result

    def test_words_have_correct_keys(self, tmp_path: Path) -> None:
        """Each word dict has word, start, end keys."""
        from bibliavox.align.api_eval import evaluate_whisper_api

        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=2.0)

        mock_response = MagicMock()
        mock_response.text = "Test"
        word = MagicMock()
        word.word = "Test"
        word.start = 0.1
        word.end = 0.9
        mock_response.words = [word]

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            result = evaluate_whisper_api(wav_path, api_key="test-key")

        assert len(result["words"]) == 1
        w = result["words"][0]
        assert "word" in w
        assert "start" in w
        assert "end" in w
        assert w["word"] == "Test"
        assert w["start"] == 0.1
        assert w["end"] == 0.9

    def test_cost_calculation_accuracy(self, tmp_path: Path) -> None:
        """Cost is calculated at $0.006/min based on audio duration."""
        from bibliavox.align.api_eval import (
            WHISPER_COST_PER_MINUTE,
            evaluate_whisper_api,
        )

        assert WHISPER_COST_PER_MINUTE == 0.006

        # 120 seconds = 2 minutes => $0.012
        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=120.0)

        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.words = []

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            result = evaluate_whisper_api(wav_path, api_key="test-key")

        assert result["duration_sec"] == pytest.approx(120.0, abs=0.1)
        assert result["cost_usd"] == pytest.approx(0.012, abs=0.001)

    def test_raises_error_when_api_key_empty(self, tmp_path: Path) -> None:
        """Function raises clear error when api_key is empty."""
        from bibliavox.align.api_eval import evaluate_whisper_api

        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=1.0)

        with pytest.raises(ValueError, match="api_key"):
            evaluate_whisper_api(wav_path, api_key="")

    def test_handles_api_errors_gracefully(self, tmp_path: Path) -> None:
        """Function handles API errors gracefully (returns error dict, doesn't crash)."""
        from bibliavox.align.api_eval import evaluate_whisper_api

        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=1.0)

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.audio.transcriptions.create.side_effect = Exception(
                "API timeout"
            )

            result = evaluate_whisper_api(wav_path, api_key="test-key")

        assert result["error"] is not None
        assert "API timeout" in result["error"]
        assert result["words"] == []
        assert result["text"] == ""
        assert result["cost_usd"] == 0.0

    def test_api_call_uses_correct_parameters(self, tmp_path: Path) -> None:
        """API is called with model=whisper-1, timestamp_granularities=[word]."""
        from bibliavox.align.api_eval import evaluate_whisper_api

        wav_path = tmp_path / "test.wav"
        self._create_wav(wav_path, duration_sec=1.0)

        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.words = []

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.audio.transcriptions.create.return_value = mock_response

            evaluate_whisper_api(wav_path, api_key="sk-test", language="hu")

        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs["model"] == "whisper-1"
        assert call_kwargs.kwargs["timestamp_granularities"] == ["word"]
        assert call_kwargs.kwargs["language"] == "hu"
        assert call_kwargs.kwargs["response_format"] == "verbose_json"

    @staticmethod
    def _create_wav(path: Path, duration_sec: float = 1.0, sr: int = 16000) -> None:
        """Create a minimal WAV file with silence."""
        n_frames = int(sr * duration_sec)
        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sr)
            wf.writeframes(b"\x00\x00" * n_frames)
