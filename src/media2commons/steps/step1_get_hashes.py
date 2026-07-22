"""Step 1: list every file in the local wiki together with its SHA-1 hash.

Reads: the local wiki API. Writes: ``data/step1_result.csv``.

The wiki's own record of what has already been transferred — the SMW properties
``UploadCommons`` and ``CommonsLink`` — is collected in the same run, so the
file list says from the start which files the source wiki considers done.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import requests

from ..config import (
    LOCAL_WIKI_API,
    LOCAL_WIKI_FILE_PAGE,
    SMW_COMMONS_PROPERTIES,
    STEP1_RESULT,
)
from ..csv_io import write_rows
from ..mediawiki import ask_property_values, iter_all_images, make_session

FIELDS = ["title", "sha1", "url", *SMW_COMMONS_PROPERTIES]


def image_row(
    image: dict,
    commons_status: dict[str, str] | None = None,
    properties: Sequence[str] = SMW_COMMONS_PROPERTIES,
) -> dict[str, str]:
    """Map an API ``allimages`` entry to an output row with a page URL."""
    title = image["title"]
    status = commons_status or {}
    return {
        "title": title,
        "sha1": image["sha1"],
        "url": LOCAL_WIKI_FILE_PAGE.format(title=title.replace(" ", "_")),
        **{prop: status.get(prop, "") for prop in properties},
    }


def collect_hashes(
    session: requests.Session,
    api_url: str = LOCAL_WIKI_API,
    properties: Sequence[str] = SMW_COMMONS_PROPERTIES,
) -> list[dict[str, str]]:
    """Every file on the wiki as an output row, with its Commons transfer status."""
    status = ask_property_values(session, api_url, properties) if properties else {}
    return [
        image_row(image, status.get(image["title"]), properties)
        for image in iter_all_images(session, api_url)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=LOCAL_WIKI_API, help="local wiki API URL")
    parser.add_argument("--output", type=Path, default=STEP1_RESULT)
    parser.add_argument(
        "--no-smw",
        action="store_true",
        help=f"leave {', '.join(SMW_COMMONS_PROPERTIES)} empty (wiki without SMW)",
    )
    args = parser.parse_args()

    session = make_session()
    properties = [] if args.no_smw else SMW_COMMONS_PROPERTIES
    rows = collect_hashes(session, args.api_url, properties)
    count = write_rows(args.output, rows, FIELDS)
    print(f"Saved {count:,} file hashes to {args.output}")


if __name__ == "__main__":
    main()
