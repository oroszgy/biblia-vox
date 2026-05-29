"""Reference data module for Bible book catalog and versification schema."""

from bibliavox.reference.books import (
    Book,
    get_all_books,
    load_books,
    lookup_by_abbreviation,
    lookup_by_usx_code,
)
from bibliavox.reference.schema import (
    BookSchema,
    get_chapter_count,
    get_verse_count,
    get_versification,
    load_versification,
)

__all__ = [
    "Book",
    "BookSchema",
    "get_all_books",
    "get_chapter_count",
    "get_verse_count",
    "get_versification",
    "load_books",
    "load_versification",
    "lookup_by_abbreviation",
    "lookup_by_usx_code",
]
