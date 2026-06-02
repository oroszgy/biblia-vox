"""MMS_FA forced alignment pipeline using torchaudio.

Provides phone-level and word-level timestamp extraction using Meta's MMS forced alignment model.
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import torch
    import torchaudio
except ImportError:
    torch = None  # type: ignore[assignment]
    torchaudio = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def align_verse(
    audio_path: Path,
    verse_text: str,
    device: str = "cuda",
) -> dict[str, Any]:
    """Align a single verse's text against audio using MMS_FA.

    Args:
        audio_path: Path to WAV file (16kHz mono PCM).
        verse_text: Known verse text to align against.
        device: "cuda" or "cpu".

    Returns:
        Dict with keys:
        - "words": list of {"word": str, "start": float, "end": float, "score": float}
        - "phones": list of {"token": str, "start": float, "end": float, "score": float}
        - "text": original verse text
    """
    bundle = torchaudio.pipelines.MMS_FA

    model = bundle.get_model(with_star=True).to(device)
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    # Load and resample audio to bundle sample rate
    waveform, sample_rate = torchaudio.load(str(audio_path))
    waveform = torchaudio.functional.resample(waveform, sample_rate, bundle.sample_rate)
    waveform = waveform.to(device)

    # Split transcript into words for tokenization
    words_list = verse_text.split() if verse_text.strip() else []

    # Handle empty transcript
    if not words_list:
        return {"words": [], "phones": [], "text": verse_text}

    # Tokenize at word level — each word produces a list of character tokens
    tokens = tokenizer(words_list)

    # Compute emission and align
    with torch.inference_mode():
        emission, _ = model(waveform)
        token_spans = aligner(emission[0], tokens)

    # Frame rate for converting frame indices to seconds
    frame_rate = bundle.sample_rate / emission.size(1)

    # Extract phone-level timestamps
    phones: list[dict[str, Any]] = []
    for word_spans in token_spans:
        for span in word_spans:
            phones.append(
                {
                    "token": span.token,
                    "start": span.start / frame_rate,
                    "end": span.end / frame_rate,
                    "score": span.score,
                }
            )

    # Group character spans into word-level timestamps
    # MMS_FA has no word-boundary token, so we use transcript word boundaries
    word_results: list[dict[str, Any]] = []
    span_idx = 0
    for word_text in words_list:
        # Count expected characters for this word
        word_char_count = len(word_text)

        # Collect spans belonging to this word
        word_spans = []
        chars_collected = 0
        while span_idx < len(phones) and chars_collected < word_char_count:
            word_spans.append(phones[span_idx])
            chars_collected += 1
            span_idx += 1

        if word_spans:
            word_start = word_spans[0]["start"]
            word_end = word_spans[-1]["end"]
            word_score = sum(s["score"] for s in word_spans) / len(word_spans)
        else:
            word_start = 0.0
            word_end = 0.0
            word_score = 0.0

        word_results.append(
            {
                "word": word_text,
                "start": word_start,
                "end": word_end,
                "score": word_score,
            }
        )

    return {"words": word_results, "phones": phones, "text": verse_text}


def align_chapter(
    audio_path: Path,
    verses: list[dict[str, str]],
    device: str = "cuda",
    use_star: bool = True,
) -> list[dict[str, Any]]:
    """Align all verses in a chapter against audio.

    Args:
        audio_path: Path to WAV file (16kHz mono PCM).
        verses: List of {"verse_id": str, "text": str}.
        device: "cuda" or "cpu".
        use_star: Whether to use <star> token for mismatch absorption.

    Returns:
        List of verse alignment results with verse_id, words, phones, start_sec, end_sec.
    """
    if not verses:
        return []

    results: list[dict[str, Any]] = []
    for verse in verses:
        verse_id = verse.get("verse_id", "")
        text = verse.get("text", "")

        if not text:
            results.append(
                {
                    "verse_id": verse_id,
                    "words": [],
                    "phones": [],
                    "start_sec": 0.0,
                    "end_sec": 0.0,
                }
            )
            continue

        alignment = align_verse(audio_path, text, device=device)

        # Determine start/end from word timestamps
        if alignment["words"]:
            start_sec = alignment["words"][0]["start"]
            end_sec = alignment["words"][-1]["end"]
        else:
            start_sec = 0.0
            end_sec = 0.0

        results.append(
            {
                "verse_id": verse_id,
                "words": alignment["words"],
                "phones": alignment["phones"],
                "start_sec": start_sec,
                "end_sec": end_sec,
            }
        )

    return results


def save_forced_alignment(
    results: list[dict[str, Any]],
    output_dir: Path,
    book: str,
    chapter: int,
) -> tuple[Path, Path]:
    """Save forced alignment results to data/aligned/.

    Writes two files per D-02 and D-05:
    - {book}_{chapter:03d}.json — verse-level timestamps
    - {book}_{chapter:03d}_phones.json — raw phone-level timestamps

    Returns:
        Tuple of (verse_path, phones_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    verse_filename = f"{book}_{chapter:03d}.json"
    phones_filename = f"{book}_{chapter:03d}_phones.json"

    verse_path = output_dir / verse_filename
    phones_path = output_dir / phones_filename

    # Verse-level output: verse_id, start_sec, end_sec, words
    verse_output = []
    for r in results:
        verse_output.append(
            {
                "verse_id": r["verse_id"],
                "start_sec": r["start_sec"],
                "end_sec": r["end_sec"],
                "words": r["words"],
            }
        )

    with open(verse_path, "w", encoding="utf-8") as f:
        json.dump(verse_output, f, ensure_ascii=False, indent=2)

    # Phone-level output: verse_id, phones
    phones_output = []
    for r in results:
        phones_output.append(
            {
                "verse_id": r["verse_id"],
                "phones": r["phones"],
            }
        )

    with open(phones_path, "w", encoding="utf-8") as f:
        json.dump(phones_output, f, ensure_ascii=False, indent=2)

    logger.info("Saved verse-level alignment to %s", verse_path)
    logger.info("Saved phone-level alignment to %s", phones_path)

    return verse_path, phones_path
