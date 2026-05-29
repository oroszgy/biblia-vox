# BibliaVox

> **Work in progress** — This project is under active development. APIs and data formats may change.

Hungarian Catholic Bible verse-to-audio alignment tool. Maps every verse of the Szent István Társulat Bible to precise timestamps in per-chapter audio recordings.

## Setup

```bash
uv sync
```

## Usage

```bash
# List all 73 Catholic Bible books
bibliavox reference list

# Look up a book by Hungarian abbreviation
bibliavox reference lookup Ter      # → GEN (Teremtés)
bibliavox reference lookup Mk       # → MRK (Márk)

# Show chapter/verse counts for a book
bibliavox reference info GEN

# Regenerate reference data from szentiras.eu source
bibliavox reference generate
```

## Development

```bash
go-task lint        # Run ruff linter
go-task format      # Format code
go-task test        # Run tests
go-task quality     # All checks
```

## Data Sources

- **Text:** szentiras.eu API (SZIT translation)
- **Audio:** mek.oszk.hu per-chapter MP3s
