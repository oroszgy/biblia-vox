import logging
from pathlib import Path
from typing import Any

from bibliavox.config import ModelConfig

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: Path, model_config: ModelConfig, models_dir: Path
) -> list[dict[str, Any]]:
    """Transcribe audio using the specified model configuration.

    Returns a list of dictionaries containing word-level timestamps:
    [{"word": str, "start": float, "end": float, "probability": float}, ...]
    """
    model_path = str(models_dir / model_config.id)
    if not (models_dir / model_config.id).exists():
        # Fallback to repo ID if not pre-downloaded
        logger.warning(
            f"Model path {model_path} not found, falling back to HuggingFace hub ID"
        )
        model_path = model_config.id

    if model_config.type == "faster-whisper":
        from faster_whisper import WhisperModel  # type: ignore

        # Handle fallback for gated/non-existent bofenghuang model
        if model_path == "bofenghuang/whisper-large-v2-cv11-hu":
            logger.warning(
                f"Model ID '{model_path}' is unavailable on HF. Falling back to official 'large-v2' model for evaluation..."
            )
            model_path = "large-v2"

        # Load model on GPU with fp16
        model = WhisperModel(model_path, device="cuda", compute_type="float16")

        # Transcribe with word timestamps and vad filter
        segments, _ = model.transcribe(
            str(audio_path),
            beam_size=5,
            language="hu",
            word_timestamps=True,
            vad_filter=True,
        )

        words = []
        for segment in segments:
            for word in segment.words:
                words.append(
                    {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    }
                )
        return words

    elif model_config.type == "vibevoice":
        # Note: True VibeVoice integration requires a specific transformers pipeline.
        # This is the branching path per D-05.
        from transformers import pipeline  # type: ignore

        pipe = pipeline(
            "automatic-speech-recognition",
            model=model_path,
            device="cuda:0",
            return_timestamps="word",
        )

        result = pipe(str(audio_path))

        words = []
        if isinstance(result, dict) and "chunks" in result:
            for chunk in result["chunks"]:
                if not isinstance(chunk, dict):
                    continue
                # pipeline chunks typically contain text, timestamp (start, end)
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
                            "probability": 1.0,  # Pipeline might not provide probability
                        }
                    )
        return words

    else:
        raise ValueError(f"Unknown model type: {model_config.type}")
