# AGENTS.md

Guidance for coding agents working in this repository. See [README.md](README.md) for
what the pipeline does; this file covers how to work on it.

## Commands

```bash
uv sync                      # create .venv and install dependencies
uv run pytest                # full test suite (fast, no network)
uv run pytest tests/test_licenses.py -k markup   # a single test
uv add <package>             # add a dependency (never edit pyproject deps by hand)
uv run m2c-step3-report      # run a pipeline step; --help lists options
```

Always run commands through `uv run` — there is no other supported way to get the
project on the import path.

## Layout

`src/media2commons/` holds the library; `src/media2commons/steps/` holds one thin CLI
module per pipeline step. Steps parse arguments, call into the library and print;
anything worth testing belongs in the library, not in a step module.

Shared logic lives in a module named for the concept, not for the step that uses it —
`licenses.py`, `dates.py`, `wikitext.py`. Steps 4 and 5 both interpret the free-form
`Lizenz` values; when they disagree, the bug is a duplicated rule, so keep the rule in
one place.

## Conventions

- Wiki endpoints, SMW property names, upload categories and all file paths live in
  `config.py`. Do not hard-code a URL or a `data/…` path anywhere else.
- Functions that talk to the network take an explicit `requests.Session` (or an
  `mwclient.Site`) as a parameter. That is what makes them testable — do not create
  sessions inside library functions.
- Rows are plain `dict[str, str]` keyed by CSV column name, read and written through
  `csv_io.py`. Column names from the source wiki stay in German (`Beschreibung`,
  `Lizenz`, `Urheber`); everything else is English.
- Type hints on public functions, `from __future__ import annotations` at the top.
- Comments explain why, not what. The existing modules are the style reference.

## Testing

Tests use pytest and live in `tests/`, one file per step or concept. **No test may touch
the network.** `tests/helpers.py` provides `FakeSession`/`FakeResponse` (queue up
responses, or a `(url, params) -> FakeResponse` callable for request-dependent replies)
and `step3_row()` for building metadata fixtures; `FakeSite` in `tests/test_step5_upload.py`
stands in for `mwclient.Site`. Use `tmp_path` for anything that writes files.

When touching license or date parsing, add the real-world input that motivated the
change as a test case — those values come from hand-edited wiki pages and the edge cases
are not guessable.

## Data and safety

- `data/` holds committed inputs and results. `data/step1_result.csv`,
  `step2_result.csv`, `step3_result.csv` and `step3_report.txt` are checked in; do not
  regenerate or overwrite them as a side effect of testing. Point steps at
  `--output /tmp/...` when smoke-testing. Note that `step3_report.txt` came from a full
  37,790-file run while the committed `step3_result.csv` is a small sample, so they do
  not match.
- Steps 2b and 5 write to live wikis — 2b edits FürthWiki's file pages, 5 uploads to
  Commons. Never run either against real endpoints without being asked; `--dry-run`
  (2b) is the safe way to try one out. Both keep an append-only log and both must keep
  asking for confirmation unless `--yes` is given.
- Step 2b rewrites existing wikitext, so it must stay a minimal edit: set the two
  parameters in the page's form template and change nothing else. `basetimestamp` on
  the edit is what stops it overwriting somebody's concurrent change — keep it.
- Step 2 makes one Commons API request per file and step 5 uploads to a live public
  wiki. Never run either against real endpoints without being asked, and keep the
  throttling defaults (`--delay`) intact. Those defaults are derived from Wikimedia's
  published per-minute rate limits (see `config.py` and the README); lowering one means
  moving into a bucket the run does not qualify for, and earns a `429`.
- Every request must carry `config.USER_AGENT` — Wikimedia throttles unidentified
  clients hardest. That is what `make_session()` is for; do not build a bare
  `requests.Session()`.
- Step 5 verifies every download's SHA-1 against the hash from step 1 before uploading.
  That check is the guard against uploading the wrong file under someone else's name —
  do not weaken or bypass it.
- Only licenses in `licenses.COMMONS_TEMPLATES` may be uploaded. Widening that set is a
  legal decision, not a code decision; ask first.
- Credentials come from the environment only, via `credentials.py`:
  `COMMONS_USERNAME`/`COMMONS_PASSWORD` for Commons, `LOCAL_WIKI_USERNAME`/
  `LOCAL_WIKI_PASSWORD` for the source wiki. Never write credentials to a file, a log
  or the repo.
