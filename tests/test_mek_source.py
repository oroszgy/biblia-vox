"""Unit tests for the MEK alternate text scraper and parser."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import httpx
from tenacity import RetryError

from bibliavox.text import mek_source
from bibliavox.text.mek_source import (
    USX_TO_MEK_PREFIX,
    build_mek_corpus,
    download_mek_book,
    parse_and_cache_mek_chapters,
    parse_mek_chapter,
)


def test_usx_to_mek_prefix_mapping() -> None:
    """Verify that USX to MEK htm prefix mapping works correctly for key examples."""
    assert USX_TO_MEK_PREFIX["GEN"] == "ter"
    assert USX_TO_MEK_PREFIX["PSA"] == "zsolt"
    assert USX_TO_MEK_PREFIX["1SA"] == "1sam"
    assert USX_TO_MEK_PREFIX["OBA"] == "abd"
    assert len(USX_TO_MEK_PREFIX) == 73


def test_download_mek_book_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should fetch from mek.oszk.hu, decoding ISO-8859-2 to UTF-8."""
    mock_response = MagicMock()
    # "árvíztűrő tükörfúrógép" encoded in latin-2
    mock_response.content = "árvíztűrő tükörfúrógép".encode("iso-8859-2")
    mock_response.status_code = 200

    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr(httpx, "get", mock_get)

    result = download_mek_book("GEN")
    assert result == "árvíztűrő tükörfúrógép"
    mock_get.assert_called_once()
    assert "ter.htm" in mock_get.call_args[0][0]


def test_download_mek_book_retry_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should retry on network errors and eventually raise RetryError or propagate exception if exhausted."""
    mock_get = MagicMock(side_effect=httpx.RequestError("Network fail"))
    monkeypatch.setattr(httpx, "get", mock_get)

    with pytest.raises((httpx.RequestError, RetryError)):
        download_mek_book("GEN")


def test_parse_and_cache_mek_chapters(tmp_path: Path) -> None:
    """Should split full book HTML into chapter-level files."""
    book_html = """
    <html>
    <body>
    <small><font color="AAAAAA"><p align=justify>Ter 1<BR></font></small>
    <small><font color="AAAAAA">Ter 1.1<BR></font></small>
    Kezdetkor teremtette Isten...
    <small><font color="AAAAAA">Ter 2<BR></font></small>
    <small><font color="AAAAAA">Ter 2.1<BR></font></small>
    Így készült el...
    </body>
    </html>
    """
    cached_files = parse_and_cache_mek_chapters("GEN", book_html, raw_dir=tmp_path)

    assert len(cached_files) == 2
    assert (tmp_path / "GEN_1.html").exists()
    assert (tmp_path / "GEN_2.html").exists()

    ch1_content = (tmp_path / "GEN_1.html").read_text(encoding="utf-8")
    assert "Ter 1" in ch1_content
    assert "Ter 1.1" in ch1_content
    assert "Ter 2" not in ch1_content


def test_parse_mek_chapter() -> None:
    """Should parse chapter HTML, extracting verses and combining suffixes."""
    chapter_html = """
    <html>
    <body>
    <small><font color="AAAAAA">Ter 2<BR></font></small>
    <small><font color="AAAAAA">Ter 2.3<BR></font></small>
    Isten megáldotta...
    <small><font color="AAAAAA">Ter 2.4a<BR></font></small>
    Ez a története az ég és a föld teremtésének, ahogy az lefolyt.<BR>
    <small><font color="AAAAAA">Ter 2.4b<BR></font></small>
    Azon a napon, amikor az Úristen a földet és az eget megalkotta,<BR>
    <small><font color="AAAAAA">Ter 2.5<BR></font></small>
    még nem volt...
    </body>
    </html>
    """
    verses = parse_mek_chapter(chapter_html)
    assert verses[3] == "Isten megáldotta..."
    # 2.4a and 2.4b should be concatenated with space
    assert (
        verses[4]
        == "Ez a története az ég és a föld teremtésének, ahogy az lefolyt. Azon a napon, amikor az Úristen a földet és az eget megalkotta,"
    )
    assert verses[5] == "még nem volt..."


def test_build_mek_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Should download missing books, split, parse, and write flat JSONL corpus."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    output_path = processed_dir / "mek.jsonl"

    # Mock download to return minimal valid book htm
    mock_book_html = """
    <html>
    <body>
    <small><font color="AAAAAA">Ter 1<BR></font></small>
    <small><font color="AAAAAA">Ter 1.1<BR></font></small>
    Kezdetkor teremtette...
    </body>
    </html>
    """

    # We will only mock download for GEN and other books will raise or be skipped
    # To speed up the test we can mock load_books to only return "GEN"
    from bibliavox.reference.books import Book

    mock_books = [
        Book(
            usx_code="GEN",
            hungarian_name="Teremtés",
            abbreviation="Ter",
            book_number=101,
            testament="OT",
            deuterocanonical=False,
        )
    ]

    monkeypatch.setattr(
        mek_source, "download_mek_book", MagicMock(return_value=mock_book_html)
    )

    # Mock load_books in the mek_source module directly
    monkeypatch.setattr(mek_source, "load_books", MagicMock(return_value=mock_books))

    total_verses = build_mek_corpus(output_path=output_path, data_dir=tmp_path)

    assert total_verses == 1
    assert output_path.exists()

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["book"] == "GEN"
    assert record["chapter"] == 1
    assert record["verse"] == 1
    assert record["text"] == "Kezdetkor teremtette..."
