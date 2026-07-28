"""Step 2: find, for every hash, the file on Commons that already has it.

Reads: ``data/step1_result.csv``. Appends to: ``data/step2_result.csv``, whose
``commons_url`` column holds the Commons file page of the match, or is empty
when the file is not on Commons yet.

The run is long and rate-limited, so results are appended row by row and an
interrupted run resumes after the rows already written. Files the source wiki
already links to on Commons are answered from step 1 instead of being looked
up again, and logging in raises the rate limit Commons applies to the rest.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from ..config import (
    ANONYMOUS_DELAY,
    AUTHENTICATED_DELAY,
    COMMONS_API,
    COMMONS_URL_FIELD,
    STEP1_RESULT,
    STEP2_RESULT,
)
from ..credentials import get_credentials
from ..csv_io import append_row, iter_rows
from ..mediawiki import commons_url_for_sha1, login, make_session
from .step1_get_hashes import FIELDS as STEP1_FIELDS

# Every input column is passed through, so the two lists cannot drift apart.
# ``commons_url`` is empty when there is no match, so the cell is truthy exactly
# when the file is already on Commons.
FIELDS = [*STEP1_FIELDS, COMMONS_URL_FIELD]

# The source wiki's own record of a completed transfer. A file it already links
# to on Commons is on Commons; asking Commons again only spends rate limit.
COMMONS_LINK_FIELD = "CommonsLink"


@dataclass
class CheckSummary:
    """What one run of :func:`check_files` did."""

    written: int = 0
    looked_up: int = 0
    matched: int = 0
    linked: int = 0
    failed: int = 0


def rows_already_done(output_path: str | Path) -> int:
    """Number of data rows already present in a partial output file."""
    output_path = Path(output_path)
    if not output_path.exists():
        return 0
    return sum(1 for _ in iter_rows(output_path))


def is_linked_to_commons(row: dict[str, str]) -> bool:
    """Whether step 1 found a ``CommonsLink`` for this file on the source wiki."""
    return bool(row.get(COMMONS_LINK_FIELD, "").strip())


def check_files(
    session: requests.Session,
    input_path: str | Path = STEP1_RESULT,
    output_path: str | Path = STEP2_RESULT,
    skip: int = 0,
    limit: int | None = None,
    delay: float = ANONYMOUS_DELAY,
    log_interval: int = 100,
    recheck_linked: bool = False,
) -> CheckSummary:
    """Append the matching Commons file page — if any — for each input row.

    Rows whose lookup fails are skipped rather than written, so a later resume
    picks them up again.
    """
    start_time = time.time()
    summary = CheckSummary()

    for index, row in enumerate(iter_rows(input_path)):
        if index < skip:
            continue
        if limit is not None and summary.written >= limit:
            break

        linked = not recheck_linked and is_linked_to_commons(row)
        if linked:
            # The source wiki already knows where the file went; use its link.
            commons_url = row[COMMONS_LINK_FIELD].strip()
            summary.linked += 1
        else:
            try:
                commons_url = commons_url_for_sha1(session, row["sha1"])
            except Exception as exc:
                print(f"Error processing '{row['title']}': {exc}")
                summary.failed += 1
                continue
            summary.looked_up += 1
            summary.matched += bool(commons_url)

        append_row(output_path, {**row, COMMONS_URL_FIELD: commons_url}, FIELDS)
        summary.written += 1

        if summary.written % log_interval == 0:
            elapsed = time.time() - start_time
            print(f"Processed {summary.written:,} rows in {elapsed:.1f}s")

        # Only a real request has to be paid for with a delay.
        if delay and not linked:
            time.sleep(delay)

    return summary


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
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help=f"seconds between requests (default {ANONYMOUS_DELAY}, "
        f"{AUTHENTICATED_DELAY} with --login)",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="log in to Commons for a higher rate limit "
        "(COMMONS_USERNAME/COMMONS_PASSWORD, or prompted)",
    )
    parser.add_argument("--username", default=None, help="Commons account name")
    parser.add_argument(
        "--recheck-linked",
        action="store_true",
        help=f"also look up files that already have a {COMMONS_LINK_FIELD}",
    )
    args = parser.parse_args()

    skip = args.skip if args.skip is not None else rows_already_done(args.output)
    if skip:
        print(f"Resuming after {skip:,} rows already in {args.output}")

    session = make_session()
    if args.login:
        username, password = get_credentials(args.username)
        try:
            login(session, username, password, COMMONS_API)
        except Exception as exc:
            raise SystemExit(f"Failed to log in to Commons: {exc}") from exc
        print(f"Logged in as {username}")

    delay = args.delay
    if delay is None:
        delay = AUTHENTICATED_DELAY if args.login else ANONYMOUS_DELAY

    summary = check_files(
        session,
        input_path=args.input,
        output_path=args.output,
        skip=skip,
        limit=args.limit,
        delay=delay,
        recheck_linked=args.recheck_linked,
    )
    print(
        f"Wrote {summary.written:,} rows to {args.output} "
        f"({summary.looked_up:,} looked up on Commons, {summary.matched:,} of them "
        f"already there; {summary.linked:,} already linked, {summary.failed:,} failed)"
    )


if __name__ == "__main__":
    main()
