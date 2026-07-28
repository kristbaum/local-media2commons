"""Step 5: download the prepared files and upload them to Wikimedia Commons.

Reads: ``data/step4_commons_ready.csv``. Writes: ``data/step5_upload_log.csv``
and the downloaded originals into ``downloads/``.

Credentials come from ``COMMONS_USERNAME``/``COMMONS_PASSWORD`` (use a bot
password) and are prompted for otherwise. Nothing is uploaded without an
explicit confirmation.
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from ..config import DOWNLOAD_DIR, STEP4_RESULT, STEP5_LOG
from ..credentials import get_credentials
from ..csv_io import iter_rows
from ..mediawiki import make_session
from ..upload_batch import run_batch
from ..uploader import CommonsUploader, UploadLog, UploadResult

UPLOAD_DELAY = 2.0


def print_result(row: dict[str, str], result: UploadResult) -> None:
    marks = {"success": "✅", "exists": "⏭️ ", "failed": "❌", "error": "❌"}
    mark = marks.get(result.status, "⚠️ ")
    detail = result.commons_url or result.error_message
    print(f"{mark} {row['commons_filename']}: {result.status} {detail}".rstrip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP4_RESULT)
    parser.add_argument("--log", type=Path, default=STEP5_LOG)
    parser.add_argument("--download-dir", type=Path, default=DOWNLOAD_DIR)
    parser.add_argument("--username", default=None, help="Commons account name")
    parser.add_argument("--start-from", type=int, default=0, help="skip N rows")
    parser.add_argument("--max-files", type=int, default=None, help="upload at most N")
    parser.add_argument("--delay", type=float, default=UPLOAD_DELAY)
    parser.add_argument(
        "--yes", action="store_true", help="skip the confirmation prompt"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}. Run step 4 first.")

    username, password = get_credentials(args.username)

    print(f"Account:      {username}")
    print(f"Input:        {args.input}")
    print(f"Start from:   row {args.start_from}")
    print(f"Max files:    {args.max_files or 'all remaining'}")
    print(f"Downloads to: {args.download_dir}")
    print(f"Log:          {args.log}")

    if not args.yes and input("\nProceed with upload? (yes/no): ").strip() != "yes":
        raise SystemExit("Upload cancelled.")

    uploader = CommonsUploader(username, password)
    try:
        uploader.connect()
    except Exception as exc:
        raise SystemExit(f"Failed to log in to Commons: {exc}") from exc
    print(f"Logged in as {username}\n")

    rows = itertools.islice(
        iter_rows(args.input),
        args.start_from,
        None if args.max_files is None else args.start_from + args.max_files,
    )

    summary = run_batch(
        rows,
        make_session(),
        uploader,
        UploadLog(args.log),
        download_dir=args.download_dir,
        delay=args.delay,
        on_result=print_result,
    )

    print("\n" + "=" * 60)
    print("BATCH UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Processed:           {summary.processed:,}")
    print(f"Uploaded:            {summary.uploaded:,}")
    print(f"Already on Commons:  {summary.skipped:,}")
    print(f"Failed:              {summary.failed:,}")
    print(f"Success rate:        {summary.success_rate:.1f}%")
    print(f"Log file:            {args.log}")


if __name__ == "__main__":
    main()
