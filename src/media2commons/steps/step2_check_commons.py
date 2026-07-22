"""Step 2: check for every hash whether that file already exists on Commons.

Reads: ``data/step1_result.csv``. Appends to: ``data/step2_result.csv``.

The run is long and rate-limited, so results are appended row by row and an
interrupted run resumes after the rows already written.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

from ..config import STEP1_RESULT, STEP2_RESULT
from ..csv_io import append_row, iter_rows
from ..mediawiki import make_session, sha1_exists_on_commons

FIELDS = ["title", "sha1", "url", "exists_on_commons"]

# Courtesy delay between Commons API calls.
REQUEST_DELAY = 0.1


def rows_already_done(output_path: str | Path) -> int:
    """Number of data rows already present in a partial output file."""
    output_path = Path(output_path)
    if not output_path.exists():
        return 0
    return sum(1 for _ in iter_rows(output_path))


def check_files(
    session: requests.Session,
    input_path: str | Path = STEP1_RESULT,
    output_path: str | Path = STEP2_RESULT,
    skip: int = 0,
    limit: int | None = None,
    delay: float = REQUEST_DELAY,
    log_interval: int = 100,
) -> int:
    """Append an ``exists_on_commons`` verdict for each input row.

    Rows whose lookup fails are skipped rather than written, so a later resume
    picks them up again.
    """
    start_time = time.time()
    processed = 0

    for index, row in enumerate(iter_rows(input_path)):
        if index < skip:
            continue
        if limit is not None and processed >= limit:
            break

        try:
            exists = sha1_exists_on_commons(session, row["sha1"])
        except Exception as exc:
            print(f"Error processing '{row['title']}': {exc}")
            continue

        append_row(output_path, {**row, "exists_on_commons": exists}, FIELDS)
        processed += 1

        if processed % log_interval == 0:
            elapsed = time.time() - start_time
            print(f"Processed {processed:,} rows in {elapsed:.1f}s")

        if delay:
            time.sleep(delay)

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP1_RESULT)
    parser.add_argument("--output", type=Path, default=STEP2_RESULT)
    parser.add_argument(
        "--skip",
        type=int,
        default=None,
        help="rows to skip; defaults to the number already in the output file",
    )
    parser.add_argument("--limit", type=int, default=None, help="stop after N rows")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY)
    args = parser.parse_args()

    skip = args.skip if args.skip is not None else rows_already_done(args.output)
    if skip:
        print(f"Resuming after {skip:,} rows already in {args.output}")

    session = make_session()
    processed = check_files(
        session,
        input_path=args.input,
        output_path=args.output,
        skip=skip,
        limit=args.limit,
        delay=args.delay,
    )
    print(f"Checked {processed:,} files. Results saved to {args.output}")


if __name__ == "__main__":
    main()
