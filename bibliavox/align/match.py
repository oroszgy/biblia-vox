import logging
from typing import Any

from rapidfuzz import fuzz  # type: ignore

logger = logging.getLogger(__name__)


def match_verses(
    verse_texts: list[dict[str, str]], word_transcripts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Match canonical verse text against transcribed words to find timestamps.

    Args:
        verse_texts: List of dicts with 'verse_id' and 'text'.
        word_transcripts: List of dicts with 'word', 'start', 'end'.

    Returns:
        List of dicts with 'verse_id', 'start_sec', 'end_sec', 'confidence_score'.
    """
    if not word_transcripts:
        return []

    # Build a single string from transcribed words and maintain character offsets
    joined_text = ""
    char_to_word_idx = {}

    for i, w in enumerate(word_transcripts):
        word_str = w["word"]
        start_char = len(joined_text)
        joined_text += word_str + " "
        end_char = len(joined_text) - 1  # Excluding the space

        # Map every character index to the word index
        for char_idx in range(start_char, end_char + 1):
            char_to_word_idx[char_idx] = i

    joined_text = joined_text.strip()
    max_char_idx = len(joined_text) - 1

    results = []

    for verse in verse_texts:
        verse_id = verse.get("verse_id", "")
        text = verse.get("text", "")
        if not text:
            continue

        # Perform partial alignment
        alignment = fuzz.partial_ratio_alignment(text, joined_text)

        if alignment is None:
            continue

        score = alignment.score
        dest_start = alignment.dest_start
        dest_end = alignment.dest_end

        # Find word indices
        start_word_idx = char_to_word_idx.get(min(dest_start, max_char_idx), 0)
        end_word_idx = char_to_word_idx.get(
            min(dest_end, max_char_idx), len(word_transcripts) - 1
        )

        start_sec = word_transcripts[start_word_idx]["start"]
        end_sec = word_transcripts[end_word_idx]["end"]

        # Extract matched transcribed text from the alignment range
        matched_text = joined_text[dest_start : dest_end + 1].strip()

        results.append(
            {
                "verse_id": verse_id,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "confidence_score": score,
                "canonical_text": text,
                "matched_text": matched_text,
            }
        )

    return results
