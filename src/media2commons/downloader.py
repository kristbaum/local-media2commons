"""Locating and fetching the original media files from the local wiki."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import requests

from .config import LOCAL_WIKI_BASE

CHUNK_SIZE = 8192

# MediaWiki serves originals from /wiki/images/<x>/<xy>/<name>; the negative
# lookahead keeps us off the thumbnail variants under /thumb/.
_FILE_URL_PATTERNS = [
    re.compile(
        r'href="(/wiki/images/[^/]+/[^/]+/[^"]*\.(?:jpg|jpeg|png|gif|pdf|svg))"'
        r'(?![^"]*thumb)',
        re.IGNORECASE,
    ),
    re.compile(
        r'src="(/wiki/images/[^/]+/[^/]+/[^"]*\.(?:jpg|jpeg|png|gif|pdf|svg))"'
        r'(?![^"]*thumb)',
        re.IGNORECASE,
    ),
]


def find_file_url(html: str, base_url: str = LOCAL_WIKI_BASE) -> str | None:
    """Extract the original (non-thumbnail) media URL from a file page's HTML."""
    for pattern in _FILE_URL_PATTERNS:
        match = pattern.search(html)
        if match:
            url = match.group(1)
            return f"{base_url}{url}" if url.startswith("/") else url
    return None


def fetch_file_url(session: requests.Session, page_url: str) -> str | None:
    """Load a local wiki file page and return the URL of the original file."""
    response = session.get(page_url)
    response.raise_for_status()
    return find_file_url(response.text)


def safe_local_name(filename: str) -> str:
    """A filename safe to write into the download directory."""
    return "".join(
        char for char in filename if char.isalnum() or char in " -_."
    ).strip()


def file_sha1(path: str | Path) -> str:
    """SHA-1 of a file's contents, matching what the MediaWiki API reports."""
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(4096), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha1(path: str | Path, expected_sha1: str) -> bool:
    """Whether a downloaded file matches the SHA-1 recorded in step 2."""
    if not expected_sha1:
        return False
    return file_sha1(path).lower() == expected_sha1.strip().lower()


def download_file(
    session: requests.Session,
    file_url: str,
    destination: str | Path,
    expected_sha1: str,
) -> Path | None:
    """Download `file_url` to `destination`, returning it only if the hash matches.

    An existing file with the right hash is kept; a mismatching one is
    re-downloaded, and a mismatching download is deleted.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and verify_sha1(destination, expected_sha1):
        return destination

    response = session.get(file_url, stream=True)
    response.raise_for_status()

    with open(destination, "wb") as handle:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                handle.write(chunk)

    if verify_sha1(destination, expected_sha1):
        return destination

    destination.unlink(missing_ok=True)
    return None
