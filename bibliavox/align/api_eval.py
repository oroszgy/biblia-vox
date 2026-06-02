"""OpenAI Whisper API evaluation for reference baseline.

Evaluates OpenAI's whisper-1 model for word-level timestamps.
Reference only — integration as alternative to local models deferred to Phase 5.5 (D-23).
"""

from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# OpenAI Whisper API pricing per D-22
WHISPER_COST_PER_MINUTE = 0.006  # USD


def evaluate_whisper_api(
    audio_path: Path,
    api_key: str,
    language: str = "hu",
) -> dict[str, Any]:
    """Evaluate OpenAI Whisper API for word-level timestamps.

    Uses whisper-1 model with word-level timestamps (D-19).
    Only whisper-1 supports timestamp_granularities=["word"] — gpt-4o-transcribe does not.

    Args:
        audio_path: Path to WAV file.
        api_key: OpenAI API key.
        language: Language code (default "hu" for Hungarian).

    Returns:
        Dict with keys:
        - "words": list of {"word": str, "start": float, "end": float}
        - "text": str (full transcription)
        - "cost_usd": float (estimated cost based on duration)
        - "duration_sec": float (audio duration)
        - "error": str or None
    """
    if not api_key:
        raise ValueError("api_key must not be empty")

    import openai

    try:
        # Get audio duration for cost calculation using stdlib wave module
        with wave.open(str(audio_path), "rb") as wf:
            n_frames = wf.getnframes()
            frame_rate = wf.getframerate()
            duration_sec = n_frames / frame_rate

        cost_usd = (duration_sec / 60) * WHISPER_COST_PER_MINUTE

        client = openai.OpenAI(api_key=api_key)

        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"],
                language=language,
            )

        words = []
        for word in response.words:
            words.append(
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                }
            )

        return {
            "words": words,
            "text": response.text,
            "cost_usd": cost_usd,
            "duration_sec": duration_sec,
            "error": None,
        }
    except Exception as e:
        logger.error(f"OpenAI API evaluation failed: {e}")
        return {
            "words": [],
            "text": "",
            "cost_usd": 0.0,
            "duration_sec": 0.0,
            "error": str(e),
        }
