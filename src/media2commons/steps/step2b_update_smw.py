"""Step 2b: write the Commons transfer status back onto the source wiki.

Reads: ``data/step2_result.csv``. Writes: ``data/step2b_update_log.csv``, and
edits file pages on the source wiki.

For every file step 2 found on Commons, the file page's form template gets
``UploadCommons=Ja`` and ``CommonsLink=<file name on Commons>``. Pages that
already say that are left untouched, so the step can be re-run at will.

Credentials come from ``LOCAL_WIKI_USERNAME``/``LOCAL_WIKI_PASSWORD`` (use a bot
password) and are prompted for otherwise. Nothing is saved without an explicit
confirmation; ``--dry-run`` never saves at all.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from ..config import LOCAL_WIKI_API, STEP2_RESULT, STEP2B_LOG
from ..credentials import local_wiki_credentials
from ..csv_io import iter_rows
from ..mediawiki import csrf_token, login, make_session
from ..smw_update import (
    DEFAULT_SUMMARY,
    UpdateLog,
    UpdateResult,
    rows_to_update,
    run_updates,
)

# The source wiki is a small installation; edits go one at a time, slowly.
EDIT_DELAY = 1.0

MARKS = {
    "updated": "✅",
    "would-update": "📝",
    "unchanged": "⏭️ ",
    "no-page": "⚠️ ",
    "no-template": "⚠️ ",
    "error": "❌",
}


def print_result(title: str, result: UpdateResult) -> None:
    detail = result.message or result.commons_filename
    mark = MARKS.get(result.status, "•")
    print(f"{mark} {title}: {result.status} {detail}".rstrip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP2_RESULT)
    parser.add_argument("--log", type=Path, default=STEP2B_LOG)
    parser.add_argument("--api-url", default=LOCAL_WIKI_API, help="source wiki API")
    parser.add_argument("--username", default=None, help="source wiki account name")
    parser.add_argument("--max-pages", type=int, default=None, help="edit at most N")
    parser.add_argument("--delay", type=float, default=EDIT_DELAY)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY, help="edit summary")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change without saving anything",
    )
    parser.add_argument(
        "--redo",
        action="store_true",
        help="also visit pages an earlier run already settled",
    )
    parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}. Run step 2 first.")

    log = UpdateLog(args.log)
    done = set() if args.redo else log.settled_titles()
    rows = rows_to_update(iter_rows(args.input), done)
    if args.max_pages is not None:
        rows = itertools.islice(rows, args.max_pages)

    print(f"Wiki:      {args.api_url}")
    print(f"Input:     {args.input}")
    print(f"Log:       {args.log}")
    print(f"Max pages: {args.max_pages or 'all remaining'}")
    if done:
        print(f"Settled:   {len(done):,} pages from earlier runs are skipped")
    if args.dry_run:
        print("Dry run:   nothing will be saved")

    session = make_session()
    token = ""
    if not args.dry_run:
        if not args.yes:
            if input("\nEdit the source wiki? (yes/no): ").strip() != "yes":
                raise SystemExit("Cancelled.")

        username, password = local_wiki_credentials(args.username)
        try:
            login(session, username, password, args.api_url)
            token = csrf_token(session, args.api_url)
        except Exception as exc:
            raise SystemExit(f"Failed to log in to the source wiki: {exc}") from exc
        print(f"Logged in as {username}\n")

    counts = run_updates(
        rows,
        session,
        token,
        log,
        api_url=args.api_url,
        summary=args.summary,
        dry_run=args.dry_run,
        delay=0.0 if args.dry_run else args.delay,
        on_result=print_result,
    )

    print("\n" + "=" * 60)
    print("SMW UPDATE SUMMARY")
    print("=" * 60)
    for status, count in counts.most_common():
        print(f"{status + ':':<14} {count:,}")
    print(f"{'Log file:':<14} {args.log}")


if __name__ == "__main__":
    main()
