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

    Uses VibeVoiceAsrForConditionalGeneration with apply_transcription_request
    for structured output with speaker, timestamps, and content per segment.

    Args:
        audio_path: Path to WAV file.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of {"word": str, "start": float, "end": float, "probability": float}.
    """
    import torch
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration  # type: ignore

    processor = AutoProcessor.from_pretrained(model_path)
    model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
    ).to(device)

    inputs = processor.apply_transcription_request(
        audio=str(audio_path),
    ).to(model.device, model.dtype)

    with torch.no_grad():
        output_ids = model.generate(**inputs)

    generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
    transcription = processor.decode(generated_ids, return_format="parsed")[0]

    # Parse structured output into word-level timestamps
    words = []
    if isinstance(transcription, list):
        for seg in transcription:
            if isinstance(seg, dict):
                content = seg.get("Content", seg.get("content", seg.get("text", "")))
                start = float(seg.get("Start", seg.get("start", 0.0)))
                end = float(seg.get("End", seg.get("end", 0.0)))
                if content:
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

    Uses apply_transcription_request with return_format="parsed" for
    structured speaker/timestamp/content output.

    Args:
        audio_path: Path to WAV file.
        model_path: HuggingFace model ID or local path.
        device: CUDA device string.

    Returns:
        List of {"text": str, "start": float, "end": float, "speaker": str}.
    """
    from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration  # type: ignore
    import torch

    processor = AutoProcessor.from_pretrained(model_path)
    model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
    ).to(device)

    inputs = processor.apply_transcription_request(
        audio=str(audio_path),
    ).to(model.device, model.dtype)

    with torch.no_grad():
        output_ids = model.generate(**inputs)

    generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
    transcription = processor.decode(generated_ids, return_format="parsed")[0]

    segments = []
    if isinstance(transcription, list):
        for seg in transcription:
            if isinstance(seg, dict):
                segments.append(
                    {
                        "text": seg.get(
                            "Content", seg.get("content", seg.get("text", ""))
                        ).strip(),
                        "start": float(seg.get("Start", seg.get("start", 0.0))),
                        "end": float(seg.get("End", seg.get("end", 0.0))),
                        "speaker": str(
                            seg.get("Speaker", seg.get("speaker", "Speaker 0"))
                        ),
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
