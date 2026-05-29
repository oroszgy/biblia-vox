"""English book name to USX code mapping for Catholic Bible books.

Maps English book names (as used in the SZIT JSON) to Paratext USX codes.
Handles all 73 Catholic Bible books:
- 66 standard books (direct English→USX mapping)
- 7 deuterocanonical books (hardcoded mapping)
"""

from __future__ import annotations

# Module-level cache for the mapping
_MAPPING: dict[str, str] | None = None

# Direct English name → USX code mapping for all 73 Catholic books
# Based on peterpolgar/Biblia-json-xml English names and books.json USX codes
_ENGLISH_TO_USX: dict[str, str] = {
    # Old Testament (39 books)
    "Genesis": "GEN",
    "Exodus": "EXO",
    "Leviticus": "LEV",
    "Numbers": "NUM",
    "Deuteronomy": "DEU",
    "Joshua": "JOS",
    "Judges": "JDG",
    "Ruth": "RUT",
    "1Samuel": "1SA",
    "2Samuel": "2SA",
    "1Kings": "1KI",
    "2Kings": "2KI",
    "1Chronicles": "1CH",
    "2Chronicles": "2CH",
    "Ezra": "EZR",
    "Nehemiah": "NEH",
    "Esther": "EST",
    "Job": "JOB",
    "Psalms": "PSA",
    "Proverbs": "PRO",
    "Ecclesiastes": "ECC",
    "SongOfSongs": "SNG",
    "Isaiah": "ISA",
    "Jeremiah": "JER",
    "Lamentations": "LAM",
    "Ezekiel": "EZK",
    "Daniel": "DAN",
    "Hosea": "HOS",
    "Joel": "JOL",
    "Amos": "AMO",
    "Obadiah": "OBA",
    "Jonah": "JON",
    "Micah": "MIC",
    "Nahum": "NAM",
    "Habakkuk": "HAB",
    "Zephaniah": "ZEP",
    "Haggai": "HAG",
    "Zechariah": "ZEC",
    "Malachi": "MAL",
    # Deuterocanonical (7 books)
    "Tobit": "TOB",
    "Judith": "JDT",
    "Wisdom": "WIS",
    "Sirach": "SIR",
    "Baruch": "BAR",
    "1Maccabees": "1MA",
    "2Maccabees": "2MA",
    # New Testament (27 books)
    "Matthew": "MAT",
    "Mark": "MRK",
    "Luke": "LUK",
    "John": "JHN",
    "Acts": "ACT",
    "Romans": "ROM",
    "1Corinthians": "1CO",
    "2Corinthians": "2CO",
    "Galatians": "GAL",
    "Ephesians": "EPH",
    "Philippians": "PHP",
    "Colossians": "COL",
    "1Thessalonians": "1TH",
    "2Thessalonians": "2TH",
    "1Timothy": "1TI",
    "2Timothy": "2TI",
    "Titus": "TIT",
    "Philemon": "PHM",
    "Hebrews": "HEB",
    "James": "JAS",
    "1Peter": "1PE",
    "2Peter": "2PE",
    "1John": "1JN",
    "2John": "2JN",
    "3John": "3JN",
    "Jude": "JUD",
    "Revelation": "REV",
}


def load_book_mapping() -> dict[str, str]:
    """Get English name → USX code mapping for all 73 Catholic books.

    Returns:
        Dict of {english_name: usx_code} for all 73 books.
    """
    global _MAPPING
    if _MAPPING is not None:
        return _MAPPING

    _MAPPING = dict(_ENGLISH_TO_USX)
    return _MAPPING


def english_to_usx(
    english_name: str,
    mapping: dict[str, str] | None = None,
) -> str:
    """Look up USX code by English book name.

    Args:
        english_name: English book name (e.g., "Genesis", "Tobit").
        mapping: Optional pre-built mapping dict. Uses cache if None.

    Returns:
        USX code string (e.g., "GEN", "TOB").

    Raises:
        KeyError: If english_name not found in mapping.
    """
    if mapping is None:
        mapping = load_book_mapping()

    if english_name not in mapping:
        raise KeyError(f"Unknown English book name: {english_name}")

    return mapping[english_name]
