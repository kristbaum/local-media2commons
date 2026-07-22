"""Uploading prepared files to Wikimedia Commons and recording the outcome."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import mwclient

from .config import COMMONS_FILE_URL, COMMONS_SITE, STEP6_LOG, USER_AGENT
from .csv_io import append_row

LOG_FIELDS = ["timestamp", "filename", "status", "commons_url", "error_message"]

DEFAULT_COMMENT = "Uploaded from FürthWiki"


class UploadLog:
    """Append-only CSV log of every upload attempt, so runs can be resumed."""

    def __init__(self, path: str | Path = STEP6_LOG):
        self.path = Path(path)

    def record(
        self,
        filename: str,
        status: str,
        commons_url: str = "",
        error_message: str = "",
    ) -> None:
        append_row(
            self.path,
            {
                "timestamp": datetime.now().isoformat(),
                "filename": filename,
                "status": status,
                "commons_url": commons_url,
                "error_message": error_message,
            },
            LOG_FIELDS,
        )


@dataclass
class UploadResult:
    """Outcome of a single upload attempt."""

    status: str
    commons_url: str = ""
    error_message: str = ""

    @property
    def uploaded(self) -> bool:
        return self.status == "success"


class CommonsUploader:
    """A logged-in mwclient session against Wikimedia Commons."""

    def __init__(self, username: str, password: str, site: mwclient.Site | None = None):
        self.username = username
        self.password = password
        self.site = site

    def connect(self) -> None:
        """Log in to Commons; raises on bad credentials or connection failure."""
        if self.site is None:
            self.site = mwclient.Site(COMMONS_SITE, clients_useragent=USER_AGENT)
        self.site.login(self.username, self.password)

    def file_exists(self, commons_filename: str) -> bool:
        return bool(self.site.pages[f"File:{commons_filename}"].exists)

    def upload(
        self,
        local_path: str | Path,
        commons_filename: str,
        wikitext: str,
        comment: str = DEFAULT_COMMENT,
    ) -> UploadResult:
        """Upload one file, skipping it if the target page already exists."""
        commons_url = COMMONS_FILE_URL.format(filename=commons_filename)

        if self.site is None:
            return UploadResult("error", error_message="Not connected to Commons")

        try:
            if self.file_exists(commons_filename):
                return UploadResult("exists", commons_url)

            with open(local_path, "rb") as handle:
                result = self.site.upload(
                    file=handle,
                    filename=commons_filename,
                    description=wikitext,
                    comment=comment,
                )
        except Exception as exc:  # network, permissions, abuse filter, ...
            return UploadResult("error", error_message=str(exc))

        if result.get("result") == "Success":
            return UploadResult("success", commons_url)

        return UploadResult(
            "failed", error_message=str(result.get("warnings", result))
        )
