"""SZIT JSON to JSONL conversion.

Converts the nested SZIT Bible dict to flat JSONL format with USX codes
and NFC normalization. One verse per line.

Input: H_Kaldi_SZIT.json (raw, Python literal format)
Output: szit.jsonl (USX codes, NFC, one verse per line)
"""

from __future__ import annotations

import json
from pathlib import Path

from bibliavox.text.mapping import load_book_mapping
from bibliavox.text.normalizer import normalize_text
from bibliavox.text.source import load_szit_json

# Repo root: 3 levels up from bibliavox/text/jsonl_converter.py
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_OUTPUT_DIR = _REPO_ROOT / "data" / "processed" / "text"


def convert_to_jsonl(
    output_path: Path | None = None,
    data_dir: Path | None = None,
) -> int:
    """Convert SZIT JSON to JSONL format.

    Each line: {"book": "GEN", "chapter": 1, "verse": 1, "text": "..."}
    Returns: number of verses written.
    """
    if output_path is None:
        output_path = _DEFAULT_OUTPUT_DIR / "szit.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = load_szit_json(data_dir)
    mapping = load_book_mapping()
    count = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for english_name, book_data in data.items():
            usx_code = mapping.get(english_name)
            if not usx_code:
                continue

            for chapter_str, verses in book_data.items():
                chapter = int(chapter_str)
                for verse_str, text in verses.items():
                    record = {
                        "book": usx_code,
                        "chapter": chapter,
                        "verse": int(verse_str),
                        "text": normalize_text(text),
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1

    return count
