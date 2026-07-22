"""Step 2: list every file in the local wiki together with its SHA-1 hash.

Reads: the local wiki API. Writes: ``data/step2_result.csv``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

from ..config import LOCAL_WIKI_API, LOCAL_WIKI_FILE_PAGE, STEP2_RESULT
from ..csv_io import write_rows
from ..mediawiki import iter_all_images, make_session

FIELDS = ["title", "sha1", "url"]


def image_row(image: dict) -> dict[str, str]:
    """Map an API ``allimages`` entry to an output row with a page URL."""
    title = image["title"]
    return {
        "title": title,
        "sha1": image["sha1"],
        "url": LOCAL_WIKI_FILE_PAGE.format(title=title.replace(" ", "_")),
    }


def collect_hashes(
    session: requests.Session, api_url: str = LOCAL_WIKI_API
) -> list[dict[str, str]]:
    """Every file on the wiki as an output row."""
    return [image_row(image) for image in iter_all_images(session, api_url)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=LOCAL_WIKI_API, help="local wiki API URL")
    parser.add_argument("--output", type=Path, default=STEP2_RESULT)
    args = parser.parse_args()

    session = make_session()
    rows = collect_hashes(session, args.api_url)
    count = write_rows(args.output, rows, FIELDS)
    print(f"Saved {count:,} file hashes to {args.output}")


if __name__ == "__main__":
    main()
