"""Step 4: pull Semantic MediaWiki metadata for every file.

Reads: ``data/step3_result.csv``. Writes: ``data/step4_result.csv``.

Titles are queried in small batches via the SMW ASK API; only files the query
returns metadata for end up in the output.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from pathlib import Path

import requests

from ..config import LOCAL_WIKI_API, SMW_PROPERTIES, STEP3_RESULT, STEP4_RESULT
from ..csv_io import read_rows, write_rows
from ..dates import normalize_smw_date
from ..mediawiki import ask, build_ask_query, make_session

# The ASK API rejects overly long queries, so keep batches conservative.
CHUNK_SIZE = 10

# Properties whose SMW value is a date record rather than a plain string.
DATE_PROPERTIES = {"Erstellungsdatum"}


def chunked(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def format_property_values(prop: str, values: list) -> str:
    """Flatten an SMW printout list into a single ``; `` separated cell."""
    if values and prop in DATE_PROPERTIES:
        first = values[0]
        raw = first.get("raw") if isinstance(first, dict) else first
        values = [normalize_smw_date(raw), *values[1:]]
    return "; ".join(str(value) for value in values)


def metadata_row(
    base_row: dict[str, str], entry: dict, properties: Sequence[str]
) -> dict[str, str]:
    """Merge one ASK result entry into the corresponding step 3 row."""
    row = dict(base_row)
    printouts = entry.get("printouts", {})
    for prop in properties:
        row[prop] = format_property_values(prop, printouts.get(prop, []))
    return row


def extract_metadata(
    session: requests.Session,
    rows: Sequence[dict[str, str]],
    properties: Sequence[str] = SMW_PROPERTIES,
    api_url: str = LOCAL_WIKI_API,
    chunk_size: int = CHUNK_SIZE,
    verbose: bool = False,
) -> list[dict[str, str]]:
    """Query SMW for every title in `rows` and return the enriched rows."""
    by_title = {row["title"]: row for row in rows}
    results: list[dict[str, str]] = []

    for chunk in chunked(list(by_title), chunk_size):
        query = build_ask_query(chunk, properties)
        if verbose:
            print(query)

        for title, entry in ask(session, api_url, query).items():
            results.append(metadata_row(by_title.get(title, {}), entry, properties))

    return results


def output_fields(
    rows: Sequence[dict[str, str]], properties: Sequence[str]
) -> list[str]:
    """Input columns followed by any property columns not already present."""
    original = list(rows[0].keys()) if rows else ["title", "sha1", "url"]
    return original + [prop for prop in properties if prop not in original]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP3_RESULT)
    parser.add_argument("--output", type=Path, default=STEP4_RESULT)
    parser.add_argument("--api-url", default=LOCAL_WIKI_API)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("-v", "--verbose", action="store_true", help="print ASK queries")
    args = parser.parse_args()

    rows = read_rows(args.input)
    session = make_session()
    results = extract_metadata(
        session,
        rows,
        api_url=args.api_url,
        chunk_size=args.chunk_size,
        verbose=args.verbose,
    )

    count = write_rows(args.output, results, output_fields(rows, SMW_PROPERTIES))
    print(f"Saved {count:,} rows to {args.output}")


if __name__ == "__main__":
    main()
