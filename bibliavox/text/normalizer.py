"""Two-stage normalization pipeline for Bible text.

Stage 1 (Lightweight normalization):
- NFC Unicode normalization (composed form)
- Line ending standardization (\r\n → \n)
- Whitespace collapse (multiple spaces → single space)
- Strip leading/trailing whitespace

Stage 2 (Schema matching) — handled by validator.py:
- Compare verse counts against versification schema
- Flag mismatches for review
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Apply Stage 1 lightweight normalization to text.

    Steps:
    1. NFC Unicode normalization (composed form)
    2. Line ending standardization (\r\n → \n)
    3. Whitespace collapse (multiple spaces → single space)
    4. Strip leading/trailing whitespace

    Args:
        text: Input text to normalize.

    Returns:
        Normalized text string.
    """
    # NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Whitespace collapse (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Strip leading/trailing whitespace (not newlines)
    text = text.strip()

    return text


def normalize_verse(text: str) -> str:
    """Normalize a single verse text.

    Args:
        text: Verse text to normalize.

    Returns:
        Normalized verse text.
    """
    return normalize_text(text)


def normalize_chapter(verses: dict[int, str]) -> dict[int, str]:
    """Normalize all verses in a chapter.

    Args:
        verses: Dict of {verse_num: verse_text} to normalize.

    Returns:
        Dict of {verse_num: normalized_verse_text}.
    """
    return {num: normalize_verse(text) for num, text in verses.items()}
