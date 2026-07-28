"""Writing the Commons transfer status back onto the source wiki's file pages.

Step 2 learns which files are already on Commons; this module puts that back
into the two Semantic MediaWiki properties the source wiki keeps for it, by
editing the form template of each file page.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

from .analysis import commons_url_of
from .config import (
    COMMONS_LINK_PROPERTY,
    LOCAL_WIKI_API,
    SMW_TRUE,
    STEP2B_LOG,
    UPLOAD_COMMONS_PROPERTY,
)
from .csv_io import append_row, iter_rows
from .mediawiki import edit_page, page_wikitext
from .wikitext import commons_filename_from_url, set_template_parameters

LOG_FIELDS = ["timestamp", "title", "status", "commons_filename", "message"]

DEFAULT_SUMMARY = "Auf Wikimedia Commons übertragen (Bot)"

# Statuses that mean the page needs no further attention, so a resumed run can
# pass over it without another lookup.
SETTLED_STATUSES = frozenset({"updated", "unchanged", "would-update"})


@dataclass
class UpdateResult:
    """Outcome of one file page."""

    status: str
    commons_filename: str = ""
    message: str = ""

    @property
    def changed(self) -> bool:
        return self.status == "updated"


class UpdateLog:
    """Append-only CSV log of every page touched, so runs can be resumed."""

    def __init__(self, path: str | Path = STEP2B_LOG):
        self.path = Path(path)

    def record(self, title: str, result: UpdateResult) -> None:
        append_row(
            self.path,
            {
                "timestamp": datetime.now().isoformat(),
                "title": title,
                "status": result.status,
                "commons_filename": result.commons_filename,
                "message": result.message,
            },
            LOG_FIELDS,
        )

    def settled_titles(self) -> set[str]:
        """Pages an earlier run already brought up to date."""
        if not self.path.exists():
            return set()
        return {
            row["title"]
            for row in iter_rows(self.path)
            if row["status"] in SETTLED_STATUSES
        }


def update_page(
    session: requests.Session,
    title: str,
    commons_url: str,
    token: str,
    api_url: str = LOCAL_WIKI_API,
    summary: str = DEFAULT_SUMMARY,
    dry_run: bool = False,
) -> UpdateResult:
    """Record `commons_url` in the SMW properties of one file page."""
    filename = commons_filename_from_url(commons_url)
    if not filename:
        return UpdateResult("error", message=f"No file name in {commons_url!r}")

    revision = page_wikitext(session, api_url, title)
    if revision is None:
        return UpdateResult("no-page", filename)

    text, timestamp = revision
    updated = set_template_parameters(
        text,
        {
            UPLOAD_COMMONS_PROPERTY: SMW_TRUE,
            COMMONS_LINK_PROPERTY: filename,
        },
    )
    if updated is None:
        return UpdateResult("no-template", filename)
    if updated == text:
        return UpdateResult("unchanged", filename)
    if dry_run:
        return UpdateResult("would-update", filename)

    edit_page(session, api_url, title, updated, summary, token, timestamp)
    return UpdateResult("updated", filename)


def rows_to_update(
    rows: Iterable[dict[str, str]], done: set[str] | None = None
) -> Iterator[dict[str, str]]:
    """The step 2 rows that have something to write back and are not done yet."""
    done = done or set()
    for row in rows:
        if commons_url_of(row) and row["title"] not in done:
            yield row


def run_updates(
    rows: Iterable[dict[str, str]],
    session: requests.Session,
    token: str,
    log: UpdateLog,
    api_url: str = LOCAL_WIKI_API,
    summary: str = DEFAULT_SUMMARY,
    dry_run: bool = False,
    delay: float = 0.0,
    on_result=None,
) -> Counter:
    """Update every given page, logging each outcome. Returns counts per status.

    A page that fails is logged and the run carries on: one bad page should not
    cost the whole batch.
    """
    counts: Counter = Counter()

    for row in rows:
        title = row["title"]
        try:
            result = update_page(
                session,
                title,
                commons_url_of(row),
                token,
                api_url=api_url,
                summary=summary,
                dry_run=dry_run,
            )
        except Exception as exc:  # network, edit conflict, permissions, ...
            result = UpdateResult("error", message=str(exc))

        log.record(title, result)
        counts[result.status] += 1
        if on_result is not None:
            on_result(title, result)

        if delay:
            time.sleep(delay)

    return counts
