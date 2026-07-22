"""MediaWiki Action API access shared by the query steps.

Every function takes an explicit :class:`requests.Session` so callers control
the user agent, retries and — in tests — substitute a fake transport.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence

import requests

from .config import COMMONS_API, USER_AGENT

# How many results to request per page of an ASK query.
ASK_PAGE_SIZE = 500

# SMW answers boolean printouts with these tokens; the rest of the pipeline
# writes Python-style booleans (see ``exists_on_commons``), so map them over.
BOOLEAN_TYPEID = "_boo"
SMW_BOOLEANS = {"t": "True", "f": "False"}


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


def ask_body(session: requests.Session, api_url: str, query: str) -> dict:
    """Run a Semantic MediaWiki ASK query and return its whole ``query`` body."""
    data = api_get(session, api_url, {"action": "ask", "query": query})
    return data.get("query", {})


def ask_results(body: dict) -> dict[str, dict]:
    """The ``results`` mapping of an ASK body, as a mapping even when empty.

    SMW serialises an empty result set as a JSON array rather than an object.
    """
    results = body.get("results")
    return results if isinstance(results, dict) else {}


def ask(session: requests.Session, api_url: str, query: str) -> dict[str, dict]:
    """Run a Semantic MediaWiki ASK query and return its ``results`` mapping."""
    return ask_results(ask_body(session, api_url, query))


def format_printout(values: Iterable, boolean: bool = False) -> str:
    """Flatten an SMW printout list into a single ``; `` separated cell."""
    if boolean:
        values = [SMW_BOOLEANS.get(value, value) for value in values]
    return "; ".join(str(value) for value in values)


def boolean_properties(body: dict) -> set[str]:
    """Names of the printed properties the wiki declares as boolean."""
    return {
        request.get("label")
        for request in body.get("printrequests", [])
        if request.get("typeid") == BOOLEAN_TYPEID
    }


def ask_property_values(
    session: requests.Session,
    api_url: str,
    properties: Sequence[str],
    page_size: int = ASK_PAGE_SIZE,
) -> dict[str, dict[str, str]]:
    """`properties` of every page that has at least one of them set.

    Asks by property rather than by title: one paged query over the property
    beats a request per batch of titles when the whole wiki has to be covered.
    """
    conditions = " OR ".join(f"[[{prop}::+]]" for prop in properties)
    printouts = "".join(f"|?{prop}" for prop in properties)

    values: dict[str, dict[str, str]] = {}
    offset = 0
    while True:
        query = f"{conditions}{printouts}|limit={page_size}|offset={offset}"
        body = ask_body(session, api_url, query)
        results = ask_results(body)
        booleans = boolean_properties(body)
        seen_before = len(values)

        for title, entry in results.items():
            printout = entry.get("printouts", {})
            values[title] = {
                prop: format_printout(printout.get(prop, []), prop in booleans)
                for prop in properties
            }

        # A wiki that ignores `offset` would otherwise replay page one forever.
        if len(results) < page_size or len(values) == seen_before:
            return values
        offset += page_size
