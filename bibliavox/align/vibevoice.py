"""VibeVoice-ASR-7B alignment with two paths: ASR+RapidFuzz and direct alignment.

Path 1: ASR → word transcripts → RapidFuzz matching (reuse match.py)
Path 2: Direct alignment → verse timestamps from VibeVoice output
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def vibevoice_asr(
    audio_path: Path,
    model_path: str = "microsoft/VibeVoice-ASR-7B",
    device: str = "cuda:0",
) -> list[dict[str, Any]]:
    """Run VibeVoice ASR to get word-level transcripts.

    Uses transformers pipeline with return_timestamps="word".
    VibeVoice processes audio in 60-second chunks internally.

    Args:
        audio_path: Path to WAV file.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of {"word": str, "start": float, "end": float, "probability": float}.
    """
    from transformers import pipeline  # type: ignore

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_path,
        device=device,
        return_timestamps="word",
    )

    result = pipe(str(audio_path))

    words = []
    if isinstance(result, dict) and "chunks" in result:
        for chunk in result["chunks"]:
            if not isinstance(chunk, dict):
                continue
            if (
                isinstance(chunk.get("timestamp"), (tuple, list))
                and len(chunk["timestamp"]) == 2
            ):
                start, end = chunk["timestamp"]
                words.append(
                    {
                        "word": chunk.get("text", "").strip(),
                        "start": start,
                        "end": end,
                        "probability": 1.0,
                    }
                )
    return words


def vibevoice_direct(
    audio_path: Path,
    model_path: str = "microsoft/VibeVoice-ASR-7B",
    device: str = "cuda:0",
) -> list[dict[str, Any]]:
    """Run VibeVoice direct alignment for verse-level timestamps.

    Uses return_format="parsed" for structured speaker/timestamp/content output.

    Args:
        audio_path: Path to WAV file.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of {"text": str, "start": float, "end": float, "speaker": str}.
    """
    from transformers import AutoProcessor, VibeVoiceForSpeechToText  # type: ignore
    import torch
    import soundfile as sf

    processor = AutoProcessor.from_pretrained(model_path)
    model = VibeVoiceForSpeechToText.from_pretrained(
        model_path, torch_dtype=torch.float16
    ).to(device)

    # Load audio
    audio, sr = sf.read(str(audio_path))
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)  # mono

    inputs = processor(audio, sampling_rate=sr, return_tensors="pt").to(device)

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=4096)

    transcription = processor.batch_decode(generated_ids, return_format="parsed")

    segments = []
    if isinstance(transcription, list):
        for seg in transcription:
            if isinstance(seg, dict):
                segments.append(
                    {
                        "text": seg.get("text", "").strip(),
                        "start": seg.get("start", 0.0),
                        "end": seg.get("end", 0.0),
                        "speaker": seg.get("speaker", "Speaker 0"),
                    }
                )
    return segments


def vibevoice_asr_match(
    audio_path: Path,
    verses: list[dict[str, str]],
    model_path: str = "microsoft/VibeVoice-ASR-7B",
    device: str = "cuda:0",
) -> list[dict[str, Any]]:
    """VibeVoice ASR + RapidFuzz matching path.

    Runs ASR to get word transcripts, then matches against known verse text.

    Args:
        audio_path: Path to WAV file.
        verses: List of {"verse_id": str, "text": str}.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of verse-level alignment results.
    """
    from bibliavox.align.match import match_verses

    words = vibevoice_asr(audio_path, model_path, device)
    return match_verses(verses, words)
