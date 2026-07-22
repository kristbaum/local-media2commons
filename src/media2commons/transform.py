"""Turning step 4 metadata rows into upload-ready Commons rows."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .analysis import row_is_on_commons
from .dates import year_string
from .licenses import is_commons_compatible, normalize_license
from .wikitext import (
    build_wikitext,
    clean_author,
    clean_description,
    clean_filename,
    clean_source,
)

COMMONS_READY_FIELDS = [
    "commons_filename",
    "original_title",
    "sha1",
    "fuerthwiki_url",
    "description",
    "date",
    "author",
    "source",
    "license",
    "wikitext",
]


def to_commons_row(row: dict[str, str], year: int | None = None) -> dict[str, str] | None:
    """Build an upload-ready row, or ``None`` if the file must not be uploaded.

    Files are skipped when they are already on Commons or when their license is
    not Commons-compatible.
    """
    if row_is_on_commons(row):
        return None

    license_name = normalize_license(row.get("Lizenz"))
    if not is_commons_compatible(license_name):
        return None

    description = clean_description(row.get("Beschreibung"))
    author = clean_author(row.get("Urheber"))
    source = clean_source(row.get("Quellangaben"))
    date = year_string(row.get("Erstellungsdatum"))
    source_url = row.get("url", "")

    return {
        "commons_filename": clean_filename(row.get("title", "")),
        "original_title": row.get("title", ""),
        "sha1": row.get("sha1", ""),
        "fuerthwiki_url": source_url,
        "description": description,
        "date": date,
        "author": author,
        "source": source,
        "license": license_name,
        "wikitext": build_wikitext(
            description=description,
            date=date,
            source=source,
            author=author,
            source_url=source_url,
            license_name=license_name,
            year=year,
        ),
    }


def transform_rows(
    rows: Iterable[dict[str, str]], year: int | None = None
) -> Iterator[dict[str, str]]:
    """Yield an upload-ready row for every uploadable input row."""
    for row in rows:
        commons_row = to_commons_row(row, year=year)
        if commons_row is not None:
            yield commons_row
