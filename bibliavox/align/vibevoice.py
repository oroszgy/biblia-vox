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
    model_path: str = "microsoft/VibeVoice-ASR-HF",
    device: str = "cuda:0",
) -> list[dict[str, Any]]:
    """Run VibeVoice ASR to get word-level transcripts.

    Uses VibeVoiceAsrForConditionalGeneration for structured output
    with speaker, timestamps, and content per segment.

    Args:
        audio_path: Path to WAV file.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of {"word": str, "start": float, "end": float, "probability": float}.
    """
    import torch
    import soundfile as sf
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration  # type: ignore

    processor = AutoProcessor.from_pretrained(model_path)
    model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
    ).to(device)

    # Load audio
    audio, sr = sf.read(str(audio_path))
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)  # mono

    inputs = processor(audio, sampling_rate=sr, return_tensors="pt").to(
        device, dtype=torch.bfloat16
    )

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=4096)

    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)

    # Parse structured output into word-level timestamps
    words = []
    if isinstance(transcription, list):
        for seg in transcription:
            if isinstance(seg, dict):
                # Structured output: {speaker, start, end, content}
                content = seg.get("content", seg.get("text", ""))
                start = seg.get("start", 0.0)
                end = seg.get("end", 0.0)
                if content:
                    # Split content into words and distribute timestamps
                    seg_words = content.strip().split()
                    if seg_words and end > start:
                        word_dur = (end - start) / len(seg_words)
                        for i, w in enumerate(seg_words):
                            words.append(
                                {
                                    "word": w,
                                    "start": start + i * word_dur,
                                    "end": start + (i + 1) * word_dur,
                                    "probability": 1.0,
                                }
                            )
            elif isinstance(seg, str):
                # Plain text output — no timestamps available
                for w in seg.strip().split():
                    words.append(
                        {
                            "word": w,
                            "start": 0.0,
                            "end": 0.0,
                            "probability": 0.5,
                        }
                    )
    return words


def vibevoice_direct(
    audio_path: Path,
    model_path: str = "microsoft/VibeVoice-ASR-HF",
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
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration  # type: ignore
    import torch
    import soundfile as sf

    processor = AutoProcessor.from_pretrained(model_path)
    model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
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
    model_path: str = "microsoft/VibeVoice-ASR-HF",
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
