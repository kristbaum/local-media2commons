"""Fake HTTP transports so no test touches the network."""

from __future__ import annotations

import json


class FakeResponse:
    """Minimal stand-in for :class:`requests.Response`."""

    def __init__(
        self,
        payload=None,
        text: str = "",
        content: bytes = b"",
        status=200,
        headers=None,
    ):
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload else "")
        self.content = content
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON body")
        return self._payload

    def iter_content(self, chunk_size=8192):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


class FakeSession:
    """Session that replays queued responses and records the calls made.

    Queue entries are either a :class:`FakeResponse` or a callable
    ``(url, params) -> FakeResponse`` for responses that depend on the request.
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, **kwargs):
        return self._respond("GET", url, params or {}, kwargs)

    def post(self, url, data=None, **kwargs):
        return self._respond("POST", url, data or {}, kwargs)

    def _respond(self, method, url, params, kwargs):
        self.calls.append(
            {"method": method, "url": url, "params": params, "kwargs": kwargs}
        )
        if not self._responses:
            raise AssertionError(f"unexpected request to {url}")
        response = self._responses.pop(0)
        return response(url, params) if callable(response) else response


def step3_row(**overrides) -> dict[str, str]:
    """A step 3 result row with sensible defaults, for building fixtures."""
    row = {
        "title": "Datei:Rathaus.jpg",
        "sha1": "abc123",
        "url": "https://www.fuerthwiki.de/wiki/index.php/Datei:Rathaus.jpg",
        "commons_url": "",
        "Beschreibung": "Das [[Rathaus]] von Fürth",
        "Erstellungsdatum": "1950-06",
        "Erstellungsjahr": "",
        "Lizenz": "cc-by-sa-3.0",
        "Person": "",
        "Quellangaben": "Stadtarchiv",
        "Urheber": "Benutzer:Someone",
    }
    row.update(overrides)
    return row
