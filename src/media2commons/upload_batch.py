"""Driving download-then-upload for a batch of step 4 rows."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import DOWNLOAD_DIR
from .downloader import download_file, fetch_file_url, safe_local_name
from .uploader import CommonsUploader, UploadLog, UploadResult


@dataclass
class BatchSummary:
    """Tally of a batch run, used for the closing report."""

    processed: int = 0
    uploaded: int = 0
    skipped: int = 0
    failed: int = 0

    def record(self, result: UploadResult) -> None:
        self.processed += 1
        if result.uploaded:
            self.uploaded += 1
        elif result.status == "exists":
            self.skipped += 1
        else:
            self.failed += 1

    @property
    def success_rate(self) -> float:
        if not self.processed:
            return 0.0
        return self.uploaded / self.processed * 100


def process_row(
    row: dict[str, str],
    session: requests.Session,
    uploader: CommonsUploader,
    download_dir: str | Path = DOWNLOAD_DIR,
) -> UploadResult:
    """Fetch one file from the local wiki and upload it to Commons."""
    commons_filename = row["commons_filename"]

    try:
        file_url = fetch_file_url(session, row["fuerthwiki_url"])
    except Exception as exc:
        return UploadResult("no_url", error_message=str(exc))

    if not file_url:
        return UploadResult(
            "no_url", error_message="Could not extract file URL from wiki page"
        )

    destination = Path(download_dir) / safe_local_name(commons_filename)
    try:
        local_path = download_file(session, file_url, destination, row["sha1"])
    except Exception as exc:
        return UploadResult("download_failed", error_message=str(exc))

    if local_path is None:
        return UploadResult(
            "download_failed", error_message="SHA-1 mismatch after download"
        )

    return uploader.upload(local_path, commons_filename, row["wikitext"])


def run_batch(
    rows: Iterable[dict[str, str]],
    session: requests.Session,
    uploader: CommonsUploader,
    log: UploadLog,
    download_dir: str | Path = DOWNLOAD_DIR,
    delay: float = 2.0,
    on_result=None,
) -> BatchSummary:
    """Process every row, logging each outcome; `delay` throttles the servers."""
    summary = BatchSummary()

    for row in rows:
        result = process_row(row, session, uploader, download_dir)
        summary.record(result)
        log.record(
            row["commons_filename"],
            result.status,
            result.commons_url,
            result.error_message,
        )
        if on_result:
            on_result(row, result)
        if delay:
            time.sleep(delay)

    return summary
