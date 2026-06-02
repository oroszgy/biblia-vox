# Testing Patterns

**Analysis Date:** 2026-06-02

## Test Framework

**Runner:**
- pytest (installed via `uv` dev dependency)
- Config: No explicit pytest config in `pyproject.toml` — uses pytest defaults

**Assertion Library:**
- pytest built-in `assert` statements (no `unittest.TestCase`)

**Run Commands:**
```bash
uv run pytest tests/ -x -v              # Run all tests, stop on first failure, verbose
uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing  # With coverage
task test                                 # Via Taskfile (equivalent to first command)
task test-cov                             # Via Taskfile (equivalent to second command)
```

## Test File Organization

**Location:**
- All tests in `tests/` directory (flat structure, no subdirectories)
- Co-located `__init__.py` (empty) for package recognition

**Naming:**
- Source module `bibliavox/reference/books.py` → `tests/test_reference.py`
- Source module `bibliavox/text/validator.py` → `tests/test_text_validator.py`
- CLI module `bibliavox/cli/text.py` → `tests/test_cli_text.py`
- CLI module `bibliavox/cli/reference.py` → `tests/test_cli_reference.py`
- CLI module `bibliavox/cli/data.py` → `tests/test_cli_data.py`

**Structure:**
```
tests/
├── __init__.py                    # Empty package marker
├── conftest.py                    # Shared fixtures (project_root)
├── test_reference.py              # reference/books.py + reference/schema.py
├── test_generate.py               # reference/generate.py constants + parse_gepi
├── test_config.py                 # config.py (Pydantic Settings)
├── test_text_source.py            # text/source.py
├── test_text_normalizer.py        # text/normalizer.py
├── test_text_validator.py         # text/validator.py
├── test_text_mapping.py           # text/mapping.py
├── test_jsonl_converter.py        # text/jsonl_converter.py
├── test_splitter.py               # text/splitter.py
├── test_mek_source.py             # text/mek_source.py
├── test_cross_validator.py        # text/cross_validator.py
├── test_audio_discovery.py        # audio/discovery.py
├── test_audio_downloader.py       # audio/downloader.py
├── test_audio_convert.py          # audio/convert.py
├── test_audio_metadata.py         # audio/metadata.py
├── test_audio_seek_index.py       # audio/seek_index.py
├── test_audio_pipeline.py         # audio/pipeline.py
├── test_cli_reference.py          # CLI integration: reference subcommand
├── test_cli_text.py               # CLI integration: text subcommand
├── test_cli_data.py               # CLI integration: data subcommand
├── test_coverage.py               # coverage.py
├── test_schema_fixes.py           # Schema correction regression tests
└── test_align.py                  # align/transcribe.py + align/match.py
```

## Test Structure

**Suite Organization:**
```python
"""Tests for the reference data module (books + schema)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bibliavox.reference.books import (
    Book,
    get_all_books,
    load_books,
    lookup_by_abbreviation,
    lookup_by_usx_code,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"


@pytest.fixture
def books() -> list[Book]:
    """Load all books for testing."""
    return load_books(DATA_DIR)


class TestBooks:
    """Tests for the book catalog."""

    def test_load_books_returns_73_books(self, books: list[Book]) -> None:
        """Catholic Bible has exactly 73 books."""
        assert len(books) == 73

    def test_lookup_ter_returns_gen(self, books: list[Book]) -> None:
        """Hungarian abbreviation 'Ter' maps to Genesis (GEN)."""
        result = lookup_by_abbreviation("Ter", books)
        assert result is not None
        assert result.usx_code == "GEN"
```

**Patterns:**
- Group related tests in classes: `class TestBooks:`, `class TestVersification:`, `class TestValidateChapter:`
- Standalone functions for simple tests: `def test_parse_m3u_extracts_extinf_and_normalized_mp3_path():`
- Docstrings on every test method describe the expected behavior
- Type annotations on fixture parameters: `books: list[Book]`, `sample_schema: BookSchema`

## Fixtures

**Shared Fixtures (`tests/conftest.py`):**
```python
"""Shared test fixtures for BibliaVox tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent
```

**Test-Specific Fixtures:**
```python
@pytest.fixture()
def sample_data(tmp_path: Path) -> Path:
    """Create a minimal SZIT JSON sample for testing."""
    data = {
        "Genesis": {
            "1": {
                "1": "Kezdetkor teremtette Isten az eget és a földet.",
                "2": "A föld puszta volt és üres.",
            },
        },
    }
    file_path = tmp_path / "H_Kaldi_SZIT.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return tmp_path


@pytest.fixture()
def sample_schema() -> BookSchema:
    """Create a sample BookSchema for testing."""
    return BookSchema(
        usx_code="GEN",
        chapter_count=2,
        chapters={1: 3, 2: 2},
    )
```

**Built-in Fixtures Used:**
- `tmp_path: Path` — Temporary directory for test artifacts (auto-cleaned)
- `monkeypatch: pytest.MonkeyPatch` — For patching functions, env vars, and module attributes

## Mocking

**Framework:** `pytest.monkeypatch` + `unittest.mock.MagicMock` + `unittest.mock.patch`

**Patterns:**

**1. Monkeypatching functions with `monkeypatch.setattr()`:**
```python
def test_download_mek_book_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = MagicMock()
    mock_response.content = "árvíztűrő tükörfúrógép".encode("iso-8859-2")
    mock_response.status_code = 200

    mock_get = MagicMock(return_value=mock_response)
    monkeypatch.setattr(httpx, "get", mock_get)

    result = download_mek_book("GEN")
    assert result == "árvíztűrő tükörfúrógép"
```

**2. Monkeypatching environment variables:**
```python
def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BIBLIAVOX_DATA_DIR", "/custom/data")
    monkeypatch.setenv("BIBLIAVOX_SZENTIRAS_API_KEY", "test-key-123")
    settings = BibliavoxSettings()
    assert settings.data_dir == Path("/custom/data")
```

**3. Monkeypatching module-level functions:**
```python
def test_prepare_chapter_writes_wav_meta_and_index_sidecars(monkeypatch, tmp_path):
    monkeypatch.setattr("bibliavox.audio.pipeline.convert_to_wav", fake_convert)
    monkeypatch.setattr(
        "bibliavox.audio.pipeline.probe_audio",
        lambda _: {"duration": 2.5, "sample_rate": 16000, ...},
    )
    monkeypatch.setattr(
        "bibliavox.audio.pipeline.build_seek_index",
        lambda *_args, **_kwargs: output_index,
    )
```

**4. Using `unittest.mock.patch` decorator:**
```python
def test_returns_correct_verse_count(self, tmp_path, sample_szit_data):
    with patch(
        "bibliavox.text.jsonl_converter.load_szit_json",
        return_value=sample_szit_data,
    ):
        count = convert_to_jsonl(output_path=output)
    assert count == 4
```

**5. Fake classes for external dependencies:**
```python
class _FakeResponse:
    def __init__(self, status_code, chunks, should_raise=False):
        self.status_code = status_code
        self._chunks = chunks
        self._should_raise = should_raise

    def raise_for_status(self):
        if self._should_raise:
            raise RuntimeError("request failed")

    def iter_bytes(self):
        return self._chunks


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def stream(self, method, url, headers=None):
        self.calls.append({"method": method, "url": url, "headers": headers or {}})
        return self._responses.pop(0)
```

**6. Mocking heavy GPU modules at module level:**
```python
# test_align.py — Mock heavy modules so tests can run without them installed
import sys
from types import ModuleType

mock_faster_whisper = ModuleType("faster_whisper")
mock_transformers = ModuleType("transformers")

sys.modules["faster_whisper"] = mock_faster_whisper
sys.modules["transformers"] = mock_transformers
```

**What to Mock:**
- External HTTP calls (`httpx.get`, `httpx.Client`)
- GPU-dependent modules (`faster_whisper`, `transformers`)
- File system operations when testing logic (use `tmp_path` for real FS operations)
- Module-level caches (reset via `reset_settings()` or direct `_VAR = None`)

**What NOT to Mock:**
- Pure logic functions (test them directly)
- Data transformations (normalizers, validators, parsers)
- File I/O with `tmp_path` (use real filesystem)

## Test Data

**Patterns:**
- Inline test data defined in fixtures or test functions
- Use `tmp_path` for file-based test data (auto-cleaned)
- Use Hungarian Bible text in tests (real domain data)
- Helper functions for creating test objects:
  ```python
  def _book(usx: str, *, deuterocanonical: bool = False) -> Book:
      return Book(
          usx_code=usx,
          hungarian_name=usx,
          abbreviation=usx,
          book_number=1,
          testament="OT",
          deuterocanonical=deuterocanonical,
      )

  def _sample_item(book: str, chapter: int, suffix: str = "") -> dict[str, object]:
      return {
          "book_usx": book,
          "chapter": chapter,
          "url": f"https://mek.oszk.hu/.../{book.lower()}-{chapter}{suffix}.mp3",
          ...
      }
  ```

**Location:**
- Test data is inline in test files (no separate fixtures directory)
- Reference data files at `data/reference/` used by integration-style tests

## Coverage

**Requirements:** No explicit coverage target enforced in CI

**View Coverage:**
```bash
uv run pytest tests/ -x -v --cov=bibliavox --cov-report=term-missing
```

**Coverage by Module (approximate from test file existence):**
| Module | Test File | Coverage Focus |
|--------|-----------|----------------|
| `reference/books.py` | `test_reference.py` | Load, lookup, cache |
| `reference/schema.py` | `test_reference.py` | Load, versification queries |
| `reference/generate.py` | `test_generate.py` | Constants, gepi parser |
| `config.py` | `test_config.py` | Settings, env vars, singleton |
| `text/source.py` | `test_text_source.py` | Load, chapter/verse extraction |
| `text/normalizer.py` | `test_text_normalizer.py` | NFC, whitespace, line endings |
| `text/validator.py` | `test_text_validator.py` | Validation, discrepancies, reports |
| `text/mapping.py` | `test_text_mapping.py` | English→USX mapping |
| `text/jsonl_converter.py` | `test_jsonl_converter.py` | Conversion, normalization, keys |
| `text/splitter.py` | `test_splitter.py` | Marker detection, splitting |
| `text/mek_source.py` | `test_mek_source.py` | Download, parse, corpus building |
| `text/cross_validator.py` | `test_cross_validator.py` | Cross-source validation |
| `audio/discovery.py` | `test_audio_discovery.py` | M3U parsing, manifest building |
| `audio/downloader.py` | `test_audio_downloader.py` | Resume, batch, retry |
| `audio/convert.py` | `test_audio_convert.py` | MP3→WAV conversion |
| `audio/metadata.py` | `test_audio_metadata.py` | Audio probing |
| `audio/seek_index.py` | `test_audio_seek_index.py` | Index building, sample window |
| `audio/pipeline.py` | `test_audio_pipeline.py` | Orchestration, skip/force |
| `coverage.py` | `test_coverage.py` | Coverage audit logic |
| `align/transcribe.py` | `test_align.py` | Transcription (mocked) |
| `align/match.py` | `test_align.py` | Verse matching |
| CLI reference | `test_cli_reference.py` | Help, list, lookup, info |
| CLI text | `test_cli_text.py` | Help, command structure |
| CLI data | `test_cli_data.py` | Coverage command |

## Test Types

**Unit Tests:**
- Majority of test suite
- Test individual functions in isolation
- Use `tmp_path` for file operations
- Mock external dependencies (HTTP, GPU modules)
- Examples: `test_reference.py`, `test_text_normalizer.py`, `test_text_validator.py`

**Integration Tests:**
- CLI integration tests using `typer.testing.CliRunner`
- Test command routing, option parsing, output formatting
- Use `monkeypatch` to mock domain functions
- Examples: `test_cli_reference.py`, `test_cli_text.py`, `test_cli_data.py`

**E2E Tests:**
- Not used. No subprocess-based CLI tests.

## CLI Testing Patterns

**Using CliRunner:**
```python
from typer.testing import CliRunner

from bibliavox.main import app

runner = CliRunner()


class TestReferenceList:
    """Tests for the `bibliavox reference list` command."""

    def test_list_shows_73_books(self) -> None:
        """bibliavox reference list should show all 73 Catholic books."""
        result = runner.invoke(app, ["reference", "list"])
        assert result.exit_code == 0
        assert "73" in result.output

    def test_list_filter_ot(self) -> None:
        """bibliavox reference list --testament OT should show only OT books."""
        result = runner.invoke(app, ["reference", "list", "--testament", "OT"])
        assert result.exit_code == 0
        assert "46" in result.output

    def test_lookup_unknown(self) -> None:
        """bibliavox reference lookup XYZ should exit with code 1."""
        result = runner.invoke(app, ["reference", "lookup", "XYZ"])
        assert result.exit_code == 1
        assert "Unknown" in result.output
```

**Mocking CLI Dependencies:**
```python
def test_data_coverage_json_exit_zero_when_complete(monkeypatch):
    monkeypatch.setattr(
        "bibliavox.cli.data.audit_coverage",
        lambda **_: {
            "summary": {"books_scoped": 66, ...},
            "complete": True,
        },
    )

    result = runner.invoke(app, ["data", "coverage", "--json"])
    assert result.exit_code == 0
```

## Common Patterns

**Async Testing:**
- Not used. All code is synchronous.

**Error Testing:**
```python
def test_raises_on_missing_book(self, sample_data: Path) -> None:
    """Should raise KeyError for non-existent book."""
    data = load_szit_json(sample_data)
    with pytest.raises(KeyError, match="NonExistent"):
        get_chapter_verses("NonExistent", 1, data)


def test_frozen(self) -> None:
    """Should be immutable (frozen dataclass)."""
    d = Discrepancy(book="GEN", chapter=1, verse=None, severity=Severity.ERROR, details="Test")
    with pytest.raises(AttributeError):
        d.book = "EXO"  # type: ignore[misc]


def test_download_mek_book_retry_on_network_error(monkeypatch):
    mock_get = MagicMock(side_effect=httpx.RequestError("Network fail"))
    monkeypatch.setattr(httpx, "get", mock_get)

    with pytest.raises((httpx.RequestError, RetryError)):
        download_mek_book("GEN")
```

**Temp Directory Testing:**
```python
def test_creates_output_directory(self, tmp_path: Path, sample_szit_data: dict) -> None:
    """Should create parent directories if they don't exist."""
    output = tmp_path / "subdir" / "deep" / "szit.jsonl"
    with patch("bibliavox.text.jsonl_converter.load_szit_json", return_value=sample_szit_data):
        convert_to_jsonl(output_path=output)
    assert output.exists()
```

**Settings Reset Pattern:**
```python
def test_get_settings_returns_singleton(self) -> None:
    """get_settings() returns the same instance on repeated calls."""
    reset_settings()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    reset_settings()  # Clean up
```

---

*Testing analysis: 2026-06-02*
