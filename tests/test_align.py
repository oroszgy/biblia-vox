import sys
from types import ModuleType

# Mock the heavy modules so tests can run without them installed locally
mock_faster_whisper = ModuleType("faster_whisper")
mock_transformers = ModuleType("transformers")

sys.modules["faster_whisper"] = mock_faster_whisper
sys.modules["transformers"] = mock_transformers

import json
from pathlib import Path
from bibliavox.config import ModelConfig
from bibliavox.align.transcribe import transcribe_audio
from bibliavox.align.match import match_verses


def test_transcribe_audio_faster_whisper(monkeypatch, tmp_path):
    class FakeWord:
        def __init__(self, word, start, end, probability):
            self.word = word
            self.start = start
            self.end = end
            self.probability = probability

    class FakeSegment:
        def __init__(self, words):
            self.words = words

    class FakeWhisperModel:
        def __init__(self, model_path, device, compute_type):
            pass

        def transcribe(
            self, audio_path, beam_size, language, word_timestamps, vad_filter
        ):
            words = [
                FakeWord("Kezdetben", 0.0, 1.0, 0.99),
                FakeWord("teremtette", 1.0, 2.0, 0.98),
                FakeWord("Isten", 2.0, 3.0, 0.97),
            ]
            return [FakeSegment(words)], None

    mock_faster_whisper.WhisperModel = FakeWhisperModel

    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"mock_wav")

    model_config = ModelConfig(id="mock-whisper", type="faster-whisper")
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "mock-whisper").mkdir()

    results = transcribe_audio(audio_path, model_config, models_dir)
    assert len(results) == 3
    assert results[0]["word"] == "Kezdetben"
    assert results[0]["start"] == 0.0
    assert results[0]["end"] == 1.0


def test_transcribe_audio_vibevoice(monkeypatch, tmp_path):
    def fake_pipeline(task, model, device, return_timestamps):
        assert task == "automatic-speech-recognition"
        assert model == str(tmp_path / "models" / "mock-vibevoice")

        def run(audio_path):
            return {
                "chunks": [
                    {"text": "Kezdetben", "timestamp": (0.0, 1.0)},
                    {"text": "teremtette", "timestamp": (1.0, 2.0)},
                ]
            }

        return run

    mock_transformers.pipeline = fake_pipeline

    audio_path = tmp_path / "test.wav"
    audio_path.write_bytes(b"mock_wav")

    model_config = ModelConfig(id="mock-vibevoice", type="vibevoice")
    models_dir = tmp_path / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / "mock-vibevoice").mkdir()

    results = transcribe_audio(audio_path, model_config, models_dir)
    assert len(results) == 2
    assert results[0]["word"] == "Kezdetben"
    assert results[0]["start"] == 0.0


def test_match_verses():
    verse_texts = [
        {"verse_id": "1", "text": "Kezdetben teremtette Isten az eget és a földet."},
        {"verse_id": "2", "text": "A föld puszta és üres volt."},
    ]
    word_transcripts = [
        {"word": "Kezdetben", "start": 0.0, "end": 0.5, "probability": 0.9},
        {"word": "teremtette", "start": 0.5, "end": 1.0, "probability": 0.9},
        {"word": "Isten", "start": 1.0, "end": 1.5, "probability": 0.9},
        {"word": "az", "start": 1.5, "end": 1.8, "probability": 0.9},
        {"word": "eget", "start": 1.8, "end": 2.2, "probability": 0.9},
        {"word": "és", "start": 2.2, "end": 2.4, "probability": 0.9},
        {"word": "a", "start": 2.4, "end": 2.5, "probability": 0.9},
        {"word": "földet", "start": 2.5, "end": 3.0, "probability": 0.9},
        {"word": "A", "start": 3.0, "end": 3.2, "probability": 0.9},
        {"word": "föld", "start": 3.2, "end": 3.5, "probability": 0.9},
        {"word": "puszta", "start": 3.5, "end": 4.0, "probability": 0.9},
        {"word": "és", "start": 4.0, "end": 4.2, "probability": 0.9},
        {"word": "üres", "start": 4.2, "end": 4.6, "probability": 0.9},
        {"word": "volt", "start": 4.6, "end": 5.0, "probability": 0.9},
    ]

    results = match_verses(verse_texts, word_transcripts)
    assert len(results) == 2
    assert results[0]["verse_id"] == "1"
    assert results[0]["start_sec"] == 0.0
    assert results[0]["end_sec"] == 3.0
    assert results[0]["confidence_score"] > 80.0
    assert results[1]["verse_id"] == "2"
    assert results[1]["start_sec"] == 3.0
    assert results[1]["end_sec"] == 5.0
