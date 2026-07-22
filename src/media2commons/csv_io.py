"""Thin helpers around ``csv.DictReader``/``DictWriter``.

Every step passes rows around as lists of dicts keyed by column name, so these
two functions cover nearly all file I/O in the pipeline.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV with a header row into a list of dicts."""
    with open(path, newline="", encoding="utf-8") as csvfile:
        return list(csv.DictReader(csvfile))


def iter_rows(path: str | Path) -> Iterator[dict[str, str]]:
    """Stream a UTF-8 CSV row by row, for files too large to hold in memory."""
    with open(path, newline="", encoding="utf-8") as csvfile:
        yield from csv.DictReader(csvfile)


def write_rows(
    path: str | Path, rows: Iterable[dict[str, object]], fieldnames: Sequence[str]
) -> int:
    """Write rows to a UTF-8 CSV with a header row and return the row count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            written += 1
    return written


def append_row(
    path: str | Path, row: dict[str, object], fieldnames: Sequence[str]
) -> None:
    """Append a single row, writing the header first if the file is still empty."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(fieldnames))
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerow(row)
