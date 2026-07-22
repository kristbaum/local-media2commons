"""MediaWiki Action API access shared by the query steps.

Every function takes an explicit :class:`requests.Session` so callers control
the user agent, retries and — in tests — substitute a fake transport.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import requests

from .config import COMMONS_API, USER_AGENT


def make_session(user_agent: str = USER_AGENT) -> requests.Session:
    """A session that identifies the bot on every request."""
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    return session


def api_get(session: requests.Session, url: str, params: dict[str, str]) -> dict:
    """GET a MediaWiki API endpoint and return the decoded JSON body."""
    response = session.get(url, params={**params, "format": "json"})
    response.raise_for_status()
    return response.json()


def iter_all_images(
    session: requests.Session, api_url: str, batch_size: int = 500
) -> Iterator[dict]:
    """Yield every file on a wiki with its SHA-1, following API continuation."""
    params = {
        "action": "query",
        "list": "allimages",
        "ailimit": str(batch_size),
        "aiprop": "sha1",
    }

    while True:
        data = api_get(session, api_url, params)
        yield from data.get("query", {}).get("allimages", [])

        cont = data.get("continue", {}).get("aicontinue")
        if not cont:
            return
        params = {**params, "aicontinue": cont}


def sha1_exists_on_commons(session: requests.Session, sha1: str) -> bool:
    """Whether a file with this SHA-1 is already on Wikimedia Commons."""
    data = api_get(
        session,
        COMMONS_API,
        {"action": "query", "list": "allimages", "aisha1": sha1},
    )
    return bool(data.get("query", {}).get("allimages"))


def build_ask_query(titles: Iterable[str], properties: Iterable[str]) -> str:
    """Build an SMW ASK query selecting `properties` for the given page titles."""
    page_filters = " OR ".join(f"[[{title}]]" for title in titles)
    property_selectors = "".join(f"|?{prop}" for prop in properties)
    return f"{page_filters}{property_selectors}"


def ask(session: requests.Session, api_url: str, query: str) -> dict[str, dict]:
    """Run a Semantic MediaWiki ASK query and return its ``results`` mapping."""
    data = api_get(session, api_url, {"action": "ask", "query": query})
    return data.get("query", {}).get("results", {})
