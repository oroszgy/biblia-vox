# Coding Conventions

**Analysis Date:** 2026-06-02

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules
- Examples: `books.py`, `schema.py`, `generate.py`, `jsonl_converter.py`, `mek_source.py`
- CLI modules match domain: `cli/reference.py`, `cli/text.py`, `cli/audio.py`

**Functions:**
- Use `snake_case` for all functions and methods
- Private functions prefixed with `_`: `_get_books_cache()`, `_resolve_book()`, `_normalize_relative_mp3_path()`
- Lookup functions use `lookup_by_<field>` pattern: `lookup_by_abbreviation()`, `lookup_by_usx_code()`
- Loader functions use `load_<thing>` pattern: `load_books()`, `load_versification()`, `load_szit_json()`

**Variables:**
- Module-level private caches: `_UPPER_SNAKE` pattern: `_BOOKS`, `_SCHEMAS`, `_SZIT_DATA`, `_MAPPING`
- Module-level path constants: `_REPO_ROOT`, `_DEFAULT_DATA_DIR`, `_DEFAULT_OUTPUT_DIR`
- Public constants: `UPPER_SNAKE_CASE`: `BASE_AUDIO_URL`, `BOOK_METADATA`, `BOOK_NUMBERS`, `REQUIRED_CODEC`

**Types:**
- Use PascalCase for classes: `Book`, `BookSchema`, `Discrepancy`, `Severity`
- Use PascalCase for TypedDicts: `DownloadResult`, `BatchSummary`, `ManifestItem`, `ParsedPlaylistItem`, `PrepareChapterResult`
- Use PascalCase for custom exceptions: `AudioConversionError`, `SeekIndexError`, `AudioProbeError`

## Code Style

**Formatting:**
- Tool: ruff (default configuration, no custom `[tool.ruff]` section in pyproject.toml)
- Format command: `uv run ruff format bibliavox/ tests/`
- Format check: `uv run ruff format --check bibliavox/ tests/`

**Linting:**
- Tool: ruff (default rules)
- Lint command: `uv run ruff check bibliavox/ tests/`
- Suppression comments used sparingly: `# noqa: BLE001` for intentional broad catches, `# noqa: S603` for subprocess calls, `# type: ignore[import-untyped]` for untyped third-party imports

**Type Checking:**
- Tool: ty (Python type checker)
- Command: `uv run ty check bibliavox/`
- All modules use `from __future__ import annotations` as first import
- Use modern union syntax: `Path | None` not `Optional[Path]`
- Use built-in generics: `list[Book]` not `List[Book]`, `dict[str, str]` not `Dict[str, str]`

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library imports (`json`, `re`, `pathlib`, `dataclasses`, `enum`, `typing`, etc.)
3. Third-party imports (`typer`, `rich`, `httpx`, `pydantic`, `tenacity`, etc.)
4. Local imports (`from bibliavox.module import ...`)

**Path Aliases:**
- No path aliases configured. All imports use full package paths: `from bibliavox.reference.books import ...`

**Patterns:**
- Use `from module import Name` for specific imports
- Use `import module` only when needed for monkeypatching in tests
- CLI modules import domain modules at top level; heavy GPU imports deferred inside functions (e.g., `from faster_whisper import WhisperModel` inside `transcribe_audio()`)

## Error Handling

**Patterns:**
- Define custom exception classes per domain:
  - `bibliavox/audio/convert.py`: `AudioConversionError(RuntimeError)`
  - `bibliavox/audio/seek_index.py`: `SeekIndexError(RuntimeError)` (referenced but defined in module)
  - `bibliavox/audio/metadata.py`: `AudioProbeError(RuntimeError)` (referenced but defined in module)
- CLI commands catch domain exceptions and convert to `typer.Exit(code=1)`:
  ```python
  try:
      result = some_operation(...)
  except AudioConversionError as exc:
      console.print(f"[red]{exc}[/red]")
      raise typer.Exit(code=1)
  ```
- Use `KeyError` for missing data lookups (books, chapters, verses)
- Use `FileNotFoundError` for missing files with descriptive messages
- Use `ValueError` for invalid input parameters
- Rich error messages with `[red]...[/red]` styling for CLI output

## Logging

**Framework:** Python standard library `logging`

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Used in alignment modules: `bibliavox/align/transcribe.py`, `bibliavox/align/match.py`
- CLI modules use `rich.console.Console` for user-facing output instead of logging
- Console output uses Rich markup: `[cyan]`, `[green]`, `[red]`, `[yellow]`, `[bold]`

## Comments

**When to Comment:**
- Module-level docstrings describe purpose, data sources, and license info
- Complex algorithms have inline comments explaining logic
- Data structures have inline attribute docstrings (triple-quoted strings after fields)

**Docstring Style:**
- Module docstrings: Multi-line with description, data source, and usage examples
  ```python
  """Bible book catalog for the 73-book Catholic canon.

  Provides the Szent István Társulat (SZIT) Hungarian translation book data:
  - Hungarian names, abbreviations
  - USX codes (Paratext standard)

  Data source: szentiras.eu tdverse schema (AGPL licensed).
  Static JSON at data/reference/books.json (no runtime network dependency).
  """
  ```
- Function docstrings: Google-style with Args, Returns, Raises sections
  ```python
  def load_books(data_dir: Path | None = None) -> list[Book]:
      """Load all Bible books from the static JSON reference data.

      Args:
          data_dir: Path to the directory containing books.json.
                    Defaults to data/reference/ relative to repo root.

      Returns:
          List of Book instances in canonical order.

      Raises:
          FileNotFoundError: If books.json is not found.
          json.JSONDecodeError: If books.json is malformed.
      """
  ```
- Dataclass field docstrings: Inline triple-quoted strings
  ```python
  @dataclass(frozen=True, slots=True)
  class Book:
      """A book of the Catholic Bible."""

      usx_code: str
      """Paratext USX code (e.g., 'GEN', 'MRK', 'BAR')."""

      hungarian_name: str
      """Hungarian name in SZIT translation (e.g., 'Teremtés', 'Márk evangéliuma')."""
  ```

## Function Design

**Size:** Functions are focused and single-purpose. Most functions are 10-40 lines. Complex CLI commands may be longer but use helper functions.

**Parameters:**
- Use keyword-only arguments (`*`) for optional configuration parameters
- Use `Path | None = None` for optional path parameters with defaults computed from `_REPO_ROOT`
- Use `typer.Option()` and `typer.Argument()` for CLI parameters with help text

**Return Values:**
- Return typed dicts (`TypedDict`) for structured results: `DownloadResult`, `BatchSummary`, `PrepareChapterResult`
- Return `list[dict]` or `dict[str, Any]` for flexible data structures
- Return `int` for count functions (e.g., `convert_to_jsonl()` returns verse count)
- Return `None` for void operations, explicit `None` return type annotation

## Module Design

**Exports:**
- No `__all__` definitions used
- Public functions are those without `_` prefix
- Modules export their key classes and functions directly

**Barrel Files:**
- `__init__.py` files are minimal (docstring only or empty)
- No re-exports from `__init__.py` modules
- Direct imports from specific modules: `from bibliavox.reference.books import load_books`

**Caching Pattern:**
- Module-level singleton cache with `_VARIABLE_NAME` pattern
- `global` keyword used to read/write cache
- Separate `reset_*()` function for test teardown:
  ```python
  _settings: BibliavoxSettings | None = None

  def get_settings() -> BibliavoxSettings:
      global _settings
      if _settings is None:
          _settings = BibliavoxSettings()
      return _settings

  def reset_settings() -> None:
      global _settings
      _settings = None
  ```

## Data Modeling

**Immutable Data:**
- Use `@dataclass(frozen=True, slots=True)` for value objects: `Book`, `BookSchema`, `Discrepancy`, `KnownGaps`
- Use `TypedDict` for typed dict structures: `DownloadResult`, `ManifestItem`, `PrepareChapterResult`
- Use `Enum` for constrained values: `Severity` with `ERROR`, `WARNING`, `INFO`

**Pydantic:**
- Use `BaseSettings` for application configuration with env var support
- Use `BaseModel` for nested configuration objects: `ModelConfig`, `ModelGauntletSettings`
- Use `SettingsConfigDict` for settings metadata (env_prefix, env_file)

## CLI Patterns

**Sub-App Structure:**
- Each domain gets its own `typer.Typer()` instance in `bibliavox/cli/<domain>.py`
- Main app in `bibliavox/main.py` registers sub-apps:
  ```python
  app = typer.Typer(name="bibliavox", help="...", no_args_is_help=True)
  app.add_typer(reference_app, name="reference", help="...")
  app.add_typer(text_app, name="text", help="...")
  app.add_typer(audio_app, name="audio", help="...")
  ```

**Command Pattern:**
- Use `@app.command()` decorator for commands
- Use `@app.command("name")` for explicit command names (e.g., `"convert-all"`, `"prepare-all"`)
- Use `@app.callback(invoke_without_command=True)` for commands that run without subcommands
- CLI entry point: `def main() -> None: app()`

**Output:**
- Use `rich.console.Console()` for all user-facing output
- Use `rich.table.Table` for tabular data
- Use `rich.progress.Progress` for batch operations with progress bars
- Use Rich markup for colored output: `[green]Success[/green]`, `[red]Error[/red]`

**Error Handling:**
- Validate inputs early, print error with `console.print(f"[red]...[/red]")`, then `raise typer.Exit(code=1)`
- Use `typer.Exit(code=0)` for explicit success exits
- Use `typer.Exit(code=1)` for all error exits

## Dependency Injection for Testability

**Patterns:**
- Functions accept optional `client` parameter for HTTP clients (e.g., `download_chapter(item, output_root, client=...)`)
- Functions accept optional `client_factory` for batch operations (e.g., `download_all(manifest, output_root, client_factory=...)`)
- Functions accept optional `executor_cls` for thread pool injection (e.g., `download_all(manifest, output_root, executor_cls=...)`)
- Functions accept optional data parameters to bypass loading (e.g., `load_books(data_dir=None)`, `get_chapter_verses(book, ch, data=None)`)
- CLI commands use `monkeypatch.setattr()` in tests to mock domain functions

---

*Convention analysis: 2026-06-02*
