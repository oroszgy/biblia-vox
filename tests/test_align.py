import sys
from types import ModuleType

# Mock the heavy modules so tests can run without them installed locally
mock_faster_whisper = ModuleType("faster_whisper")
mock_transformers = ModuleType("transformers")

sys.modules["faster_whisper"] = mock_faster_whisper
sys.modules["transformers"] = mock_transformers

import json  # noqa: E402
from bibliavox.config import ModelConfig  # noqa: E402
from bibliavox.align.transcribe import transcribe_audio  # noqa: E402
from bibliavox.align.match import match_verses  # noqa: E402


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


def test_evaluate_gold_command(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from bibliavox.config import reset_settings
    from bibliavox.main import app

    # Setup mock environment
    monkeypatch.setenv("BIBLIAVOX_DATA_DIR", str(tmp_path))
    reset_settings()

    # Create dummy canonical verses
    text_dir = tmp_path / "processed" / "text"
    text_dir.mkdir(parents=True)
    mek_path = text_dir / "mek.jsonl"

    gold_chapters = [
        ("TIT", 1),
        ("TIT", 2),
        ("TIT", 3),
        ("ZEP", 1),
        ("ZEP", 2),
        ("ZEP", 3),
        ("TOB", 1),
        ("TOB", 2),
        ("TOB", 3),
        ("TOB", 4),
    ]

    with open(mek_path, "w", encoding="utf-8") as f:
        for book, ch in gold_chapters:
            # Add one verse per chapter
            f.write(
                json.dumps(
                    {
                        "book": book,
                        "chapter": ch,
                        "verse": 1,
                        "text": "Kezdetben teremtette Isten az eget és a földet.",
                    }
                )
                + "\n"
            )

            # Create a mock WAV file for each
            audio_dir = tmp_path / "prepared" / "audio" / book
            audio_dir.mkdir(parents=True, exist_ok=True)
            (audio_dir / f"{ch:03d}.wav").write_bytes(b"mock_wav")

    # Mock transcribe_audio to return mock words
    def mock_transcribe(audio_path, model_config, models_dir):
        return [
            {"word": "Kezdetben", "start": 0.0, "end": 1.0, "probability": 0.99},
            {"word": "teremtette", "start": 1.0, "end": 2.0, "probability": 0.99},
        ]

    monkeypatch.setattr("bibliavox.cli.align.transcribe_audio", mock_transcribe)

    # Run CLI command
    runner = CliRunner()
    result = runner.invoke(app, ["align", "evaluate-gold"])

    assert result.exit_code == 0

    # Check outputs exist
    summary_path = tmp_path / "processed" / "evaluation" / "summary.json"
    assert summary_path.exists()

    with open(summary_path, "r", encoding="utf-8") as sf:
        summary = json.load(sf)

    # Assert model keys are present in summary
    assert "bofenghuang/whisper-large-v2-cv11-hu" in summary
    model_sum = summary["bofenghuang/whisper-large-v2-cv11-hu"]
    assert model_sum["total_canonical"] == 10
    assert model_sum["total_aligned"] == 10
    assert model_sum["overall_coverage_pct"] == 100.0
    assert len(model_sum["chapters"]) == 10

    # Clean up environment
    reset_settings()
