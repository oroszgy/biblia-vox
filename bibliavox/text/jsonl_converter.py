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
    raise NotImplementedError("GREEN phase not implemented yet")
