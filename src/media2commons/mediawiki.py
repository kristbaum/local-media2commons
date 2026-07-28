"""MediaWiki Action API access shared by the query steps.

Every function takes an explicit :class:`requests.Session` so callers control
the user agent, retries and — in tests — substitute a fake transport.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Iterator, Sequence

import requests

from .config import COMMONS_API, COMMONS_FILE_URL, USER_AGENT

# How many results to request per page of an ASK query.
ASK_PAGE_SIZE = 500

# Wikimedia answers 429 once a client is over its rate limit and 503 when the
# backend is lagging. Both mean "come back later", not "this row is broken", so
# they are waited out instead of being reported as a failed lookup.
RETRY_STATUSES = frozenset({429, 503})
MAX_RETRIES = 5

# What to wait when a 429 arrives without a Retry-After header; Wikimedia asks
# for at least five seconds, doubling per attempt.
BASE_RETRY_WAIT = 5.0

# SMW answers boolean printouts with these tokens; the pipeline writes
# Python-style booleans (see the ``UploadCommons`` column), so map them over.
BOOLEAN_TYPEID = "_boo"
SMW_BOOLEANS = {"t": "True", "f": "False"}


def make_session(user_agent: str = USER_AGENT) -> requests.Session:
    """A session that identifies the bot on every request."""
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    return session


def retry_wait(response, attempt: int, base: float = BASE_RETRY_WAIT) -> float:
    """Seconds to wait before retrying, honouring a ``Retry-After`` header."""
    header = getattr(response, "headers", {}).get("Retry-After", "")
    try:
        return max(0.0, float(header))
    except (TypeError, ValueError):
        # Retry-After may also be an HTTP date; back off exponentially instead.
        return base * 2**attempt


def api_get(
    session: requests.Session,
    url: str,
    params: dict[str, str],
    retries: int = MAX_RETRIES,
) -> dict:
    """GET a MediaWiki API endpoint and return the decoded JSON body.

    Rate-limit and overload responses are retried after the wait the server
    asks for, so a throttled run slows down rather than losing rows.
    """
    for attempt in range(retries + 1):
        response = session.get(url, params={**params, "format": "json"})
        if response.status_code not in RETRY_STATUSES or attempt == retries:
            break

        wait = retry_wait(response, attempt)
        print(f"HTTP {response.status_code} from the API; waiting {wait:.0f}s")
        time.sleep(wait)

    response.raise_for_status()
    return response.json()


def api_post(session: requests.Session, url: str, params: dict[str, str]) -> dict:
    """POST to a MediaWiki API endpoint and return the decoded JSON body."""
    response = session.post(url, data={**params, "format": "json"})
    response.raise_for_status()
    return response.json()


def login(
    session: requests.Session,
    username: str,
    password: str,
    api_url: str = COMMONS_API,
) -> None:
    """Log `session` in to a wiki, raising if the credentials are rejected.

    Authenticated clients get a much higher API rate limit than anonymous ones,
    which is what makes the per-file lookups of step 2 survive a full run. Use a
    bot password; the login cookies then ride along on every later request.
    """
    tokens = api_get(
        session, api_url, {"action": "query", "meta": "tokens", "type": "login"}
    )
    token = tokens.get("query", {}).get("tokens", {}).get("logintoken")
    if not token:
        raise RuntimeError("The API did not return a login token")

    result = api_post(
        session,
        api_url,
        {
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": token,
        },
    ).get("login", {})

    if result.get("result") != "Success":
        # `reason` carries the wiki's message; never echo the password.
        raise RuntimeError(
            f"Login failed: {result.get('reason') or result.get('result') or result}"
        )


def csrf_token(session: requests.Session, api_url: str) -> str:
    """The edit token for the logged-in session on this wiki."""
    data = api_get(session, api_url, {"action": "query", "meta": "tokens"})
    token = data.get("query", {}).get("tokens", {}).get("csrftoken")
    if not token or token == "+\\":
        raise RuntimeError("No edit token; the session is not logged in")
    return token


def page_wikitext(
    session: requests.Session, api_url: str, title: str
) -> tuple[str, str] | None:
    """The current wikitext of a page and its revision timestamp.

    ``None`` when the page does not exist — plenty of files were uploaded
    without ever getting a description page.
    """
    data = api_get(
        session,
        api_url,
        {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvprop": "content|timestamp",
            "rvslots": "main",
            "formatversion": "2",
        },
    )
    pages = data.get("query", {}).get("pages") or []
    if not pages or pages[0].get("missing"):
        return None

    revisions = pages[0].get("revisions") or []
    if not revisions:
        return None

    revision = revisions[0]
    content = revision.get("slots", {}).get("main", {}).get("content", "")
    return content, revision.get("timestamp", "")


def edit_page(
    session: requests.Session,
    api_url: str,
    title: str,
    text: str,
    summary: str,
    token: str,
    basetimestamp: str = "",
) -> dict:
    """Replace a page's wikitext, raising on anything but a saved edit.

    `basetimestamp` is the revision the new text was built from; the wiki
    rejects the edit if someone else has saved since.
    """
    params = {
        "action": "edit",
        "title": title,
        "text": text,
        "summary": summary,
        "token": token,
        # Step 2b annotates existing file pages; it must never create one.
        "nocreate": "1",
        "assert": "user",
    }
    if basetimestamp:
        params["basetimestamp"] = basetimestamp

    data = api_post(session, api_url, params)
    if "error" in data:
        error = data["error"]
        raise RuntimeError(f"{error.get('code')}: {error.get('info', error)}")

    result = data.get("edit", {})
    if result.get("result") != "Success":
        raise RuntimeError(f"Edit not saved: {result or data}")
    return result


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


def commons_url_for_sha1(session: requests.Session, sha1: str) -> str:
    """The Commons file page of the file with this SHA-1, or ``""`` if there is none.

    Commons may hold the same bytes under several names; the first match is
    enough to say the file is already there, and names the copy to link to.
    """
    data = api_get(
        session,
        COMMONS_API,
        {"action": "query", "list": "allimages", "aisha1": sha1},
    )
    matches = data.get("query", {}).get("allimages") or []
    if not matches:
        return ""

    match = matches[0]
    if match.get("descriptionurl"):
        return match["descriptionurl"]

    # Only reachable if the API stops sending descriptionurl by default.
    name = match.get("name") or match.get("title", "").removeprefix("File:")
    return COMMONS_FILE_URL.format(filename=name) if name else ""


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
