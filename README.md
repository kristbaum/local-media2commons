# Local-Media-2-Commons

A pipeline to sync local MediaWiki media files to Wikimedia Commons.
It is currently configured for [FürthWiki](https://www.fuerthwiki.de), with the goal of
making the process repeatable so imports can be re-run as the source wiki grows.

## Setup

The project is managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync          # create .venv and install dependencies
uv run pytest    # run the test suite
```

## How it works

The pipeline is a chain of steps. Each one reads the CSV the previous step wrote and
writes its own into [data/](data/), so a step can be re-run or inspected in isolation.
Every step lives in [src/media2commons/steps/](src/media2commons/steps/) and is exposed
both as a console script and as a module.

| Step | Command | Reads | Writes |
| --- | --- | --- | --- |
| 1. List files, hashes, transfer status | `uv run m2c-step1-hashes` | local wiki API | `data/step1_result.csv` |
| 2. Find matches on Commons | `uv run m2c-step2-commons-check` | `step1_result.csv` | `data/step2_result.csv` |
| 2b. Write the status back to the source wiki | `uv run m2c-step2b-update-smw` | `step2_result.csv` | source wiki, `data/step2b_update_log.csv` |
| 3. Extract SMW metadata | `uv run m2c-step3-metadata` | `step2_result.csv` | `data/step3_result.csv` |
| 3b. Analysis report | `uv run m2c-step3-report` | `step3_result.csv` | `data/step3_report.txt` |
| 4. Transform for Commons | `uv run m2c-step4-transform` | `step3_result.csv` | `data/step4_commons_ready.csv` |
| 5. Upload | `uv run m2c-step5-upload` | `step4_commons_ready.csv` | `data/step5_upload_log.csv` |

Every step takes `--input`/`--output` overrides; run any of them with `--help` for the
full set of options.

### Step 1 — collect file hashes and transfer status

Pages through the `list=allimages` API of the local wiki with `aiprop=sha1`, following
continuation until every file is listed, and records title, SHA-1 and file page URL.
This is the query it issues, and the one to reach for when listing FürthWiki's files by
hand:

```text
https://www.fuerthwiki.de/wiki/api.php?action=query&list=allimages&ailimit=500&aiprop=sha1&format=json
```

Each response carries a `continue.aicontinue` token that has to be passed back as
`&aicontinue=…` until it stops appearing — one page of 500 files is nowhere near the
whole wiki.

The same run also reads what the wiki itself says about Commons, into two more columns:

| Column | SMW property | Meaning |
| --- | --- | --- |
| `UploadCommons` | [Attribut:UploadCommons](https://www.fuerthwiki.de/wiki/index.php?title=Attribut:UploadCommons) | boolean — the file is on Commons |
| `CommonsLink` | [Attribut:CommonsLink](https://www.fuerthwiki.de/wiki/index.php?title=Attribut:CommonsLink) | text — link to the file page on Commons |

These are asked for by property rather than per title, so covering the whole wiki costs a
handful of paged queries instead of one request per file:

```text
https://www.fuerthwiki.de/wiki/api.php?action=ask&query=[[UploadCommons::%2B]] OR [[CommonsLink::%2B]]|?UploadCommons|?CommonsLink|limit=500|offset=0&format=json
```

Paging continues with `offset=500`, `1000`, … until a page comes back short. A file the
query says nothing about keeps both cells empty, which is distinct from an explicit
`False`. SMW answers booleans with `t`/`f`; they are written out as `True`/`False`. Use
`--no-smw` on a wiki without Semantic MediaWiki: the columns stay in the CSV but are
left empty.

As of July 2026 the source wiki marks 733 files `UploadCommons=true` and sets
`CommonsLink` on none, so the column is currently a record of past manual transfers
rather than of anything this pipeline did.

### Step 2 — find what is already on Commons

Looks each SHA-1 up via `list=allimages&aisha1=…` on Commons; a non-empty result means
the identical file is already there. This is the long-running step (one request per
file, throttled by `--delay`), so results are appended row by row and an interrupted run
resumes automatically after the rows already in the output file. Use `--skip`/`--limit`
to process an explicit window.

```text
https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aisha1=fcdfc17fac0c39e6f201f2022f9f1f9f8b35d449&format=json
```

The `commons_url` column holds the `descriptionurl` of the match — the Commons file page
carrying those exact bytes — and is empty when there is none, so the cell both answers
the question and says which file answered it:

| `commons_url` | Meaning |
| --- | --- |
| `https://commons.wikimedia.org/wiki/File:…` | the identical file is on Commons, here |
| *(empty)* | not on Commons |

Commons can hold the same bytes under several names; the first match is the one
recorded. Files that already carry a `CommonsLink` from step 1 get that link written
straight through without asking Commons — the source wiki has already answered the
question. `--recheck-linked` looks them up anyway.

Everything downstream treats the column as "non-empty means on Commons"
([`row_is_on_commons`](src/media2commons/analysis.py)). The column was called
`exists_on_commons` and held `True`/`False` until July 2026; result files from before
then are still read correctly, so an interrupted run can be resumed into one.

#### Staying inside Commons' rate limit

Wikimedia [rate-limits the API](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits)
per minute, and answers a client that is over its limit with `429 Too Many Requests`:

| Client | Limit |
| --- | --- |
| No identifying User-Agent | 10 req/min |
| Bot identified only by its User-Agent | 200 req/min |
| Authenticated, new account | 200 req/min |
| Authenticated, established editor | 2,000 req/min |
| Account with the bot flag | exempt |

So yes — logging in raises the ceiling, tenfold for an established account. Every request
already carries the `USER_AGENT` from [config.py](src/media2commons/config.py) (Wikimedia
requires a tool name plus a contact URL or e-mail), which is what keeps the run out of
the 10/min bucket.

`--delay` therefore defaults to 0.5 s (120 req/min) anonymously, and to 0.1 s
(600 req/min) with `--login`, which uses the same `COMMONS_USERNAME`/`COMMONS_PASSWORD`
[bot password](https://commons.wikimedia.org/wiki/Special:BotPasswords) as step 5. The
0.1 s default assumes an established account; on a fresh one pass `--delay 0.5`.

```bash
COMMONS_USERNAME=YourBot COMMONS_PASSWORD=… uv run m2c-step2-commons-check --login
```

A `429` (or a `503` from an overloaded backend) is no longer counted as a failed lookup:
the request waits out the server's `Retry-After` and is retried, backing off
exponentially from 5 s when no such header is sent.

### Step 2b — write the status back to the source wiki

Step 2 discovers what is already on Commons; this step tells the source wiki about it,
so the two `UploadCommons`/`CommonsLink` columns step 1 reads stop being a record of
manual transfers only. Every row with a `commons_url` has its file page edited:

```diff
 |ZeigeNichtInStraße=Nein
-|UploadCommons=Nein
+|UploadCommons=Ja
 |Erstellungsdatum=1971
 |Beschreibung=Luftbild des "alten" Gänsbergs zu Beginn der [[Flächensanierung]], ca. 1971
+|CommonsLink='Alter' Gänsberg.jpg
 }}
```

`CommonsLink` is the file name the URL points at — everything after `File:`,
percent-decoded, with the URL's underscores turned back into spaces. The properties are
set as parameters of the page's form template (`{{Bild}}`, `{{Audio}}`, `{{Video}}`),
which is how everything else on those pages is stored; existing parameters are
overwritten in place and missing ones appended, leaving the rest of the page byte for
byte as it was. A page that already says both is left alone, so the step is safe to
re-run and only ever writes the pages that need it.

This is the one step that writes to the source wiki, so: it asks for confirmation unless
`--yes`, `--dry-run` reports what would change without logging in at all, `--max-pages`
bounds a run, and every page is logged to `data/step2b_update_log.csv` — a later run
skips what that log already settled (`--redo` visits them anyway). Credentials come from
`LOCAL_WIKI_USERNAME`/`LOCAL_WIKI_PASSWORD` and are prompted for otherwise. Start with a
dry run:

```bash
uv run m2c-step2b-update-smw --dry-run --max-pages 20
LOCAL_WIKI_USERNAME=YourBot LOCAL_WIKI_PASSWORD=… uv run m2c-step2b-update-smw --max-pages 5
```

#### `CommonsLink` has to be declared on the wiki first

The form module only stores parameters that belong to an attribute's class, and
[Attribut:CommonsLink](https://www.fuerthwiki.de/wiki/index.php?title=Attribut:CommonsLink)
currently declares only its datatype:

```wikitext
{{Attribut|Datentyp=Text}}
{{Attribut/Hilfe}}
```

Every stored attribute — `UploadCommons`, `Quellangaben`, `Beschreibung` — also has an
`{{Attribut/Klasse}}` block, and a parse probe confirms that `{{Bild|CommonsLink=…}}` is
dropped today while `{{Bild|Quellangaben=…}}` is kept. Until a block like this is added
to that page, step 2b's edits will set `UploadCommons` but `CommonsLink` will not become
a queryable property:

```wikitext
{{Attribut/Klasse
|KlassenName=Default
|FieldArgs=input type{{=}}text{{!}}size{{=}}65
|Infotext=Dateiname auf Wikimedia Commons
}}
```

### Step 3 — extract metadata

Queries the Semantic MediaWiki ASK API in batches of 10 titles for the properties
`Beschreibung`, `Erstellungsdatum`, `Erstellungsjahr`, `Lizenz`, `Person`,
`Quellangaben` and `Urheber`. SMW's raw date format (`1/1754/8/12`) is normalised to
`YYYY`, `YYYY-MM` or `YYYY-MM-DD`. Only files SMW returns metadata for reach the output.

The companion report step summarises license distribution, creation years and metadata
completeness, and estimates how many files are actually uploadable.

### Step 4 — transform for Commons

Filters to the files that may be uploaded — not already on Commons **and** carrying a
Commons-compatible license (CC-BY-SA-3.0/4.0, CC-BY-3.0/4.0, Public Domain, GFDL) — and
renders a complete file description page for each:

```mediawiki
=={{int:filedesc}}==
{{Information
|description={{de|1=…}}
|date=1971
|source=[https://www.fuerthwiki.de/wiki/index.php/Datei:… FürthWiki] - …
|author=…
|permission=
|other_versions=
}}

=={{int:license-header}}==
{{self|CC-BY-SA-3.0}}

[[Category:Images from FürthWiki]]
[[Category:Media uploaded from FürthWiki (2026)]]
```

The `Lizenz` property is free-form text on the source wiki — anything from a clean
`cc-by-sa-3.0` to a whole wiki table pasted into the field — so values are stripped of
markup and mapped onto canonical names before the compatibility check
([licenses.py](src/media2commons/licenses.py)).

### Step 5 — upload

For each prepared row: resolve the original (non-thumbnail) file URL from its wiki page,
download it, verify the SHA-1 against the hash recorded in step 1, and upload it to
Commons via `mwclient`. Files whose hash does not match are never uploaded, and a file
that already exists on Commons is skipped. Every attempt is logged to
`data/step5_upload_log.csv`.

Credentials are read from `COMMONS_USERNAME` and `COMMONS_PASSWORD` (use a
[bot password](https://commons.wikimedia.org/wiki/Special:BotPasswords)) and prompted for
otherwise. The run asks for confirmation unless `--yes` is given. Start small:

```bash
COMMONS_USERNAME=YourBot COMMONS_PASSWORD=… uv run m2c-step5-upload --max-files 5
```

## Project layout

```text
src/media2commons/
  config.py        endpoints, SMW properties, file paths
  credentials.py   Commons credentials from the environment or a prompt
  csv_io.py        CSV read/write/append helpers
  mediawiki.py     MediaWiki + SMW API access, login, editing, rate-limit retries
  licenses.py      license normalisation and Commons compatibility
  dates.py         SMW date parsing and year extraction
  wikitext.py      Commons page rendering, source wiki form-template editing
  smw_update.py    writing the transfer status back onto source wiki pages
  transform.py     step 3 rows -> upload-ready rows
  analysis.py      statistics over the metadata dump
  reporting.py     text rendering of those statistics
  downloader.py    file URL resolution, download, SHA-1 verification
  uploader.py      Commons login, upload, upload log
  upload_batch.py  per-file and batch orchestration for step 5
  steps/           one CLI entry point per pipeline step
tests/             pytest suite; no test touches the network
data/              inputs and results of each step
```

## Pointing this at another wiki

Everything wiki-specific lives in [config.py](src/media2commons/config.py): API
endpoints, the SMW property names, and the categories added to uploads. The
German-language assumptions (the `Datei:` namespace prefix, `{{de|1=…}}` descriptions,
the `Benutzer:` prefix) are in [wikitext.py](src/media2commons/wikitext.py).

## Open questions

Most files tagged with a CC license on FürthWiki are in fact more strictly licensed. A
game should let people determine whether images are truly correctly licensed, by showing
the structured data and wikitext alongside the image. Using InstantCommons would be nice
too.

If the license is in question:

* Remove the CC template from FürthWiki (hard)
* Change the semantic license on FürthWiki to copyrighted (doable; maybe clean up the
  difference afterwards)
* Don't upload to Commons

If the license is correct:

* Upload to Commons:
  * Include wikitext with the `{{Information}}` template
  * Add structured data for the license
  * Backlink to FürthWiki
* Change FürthWiki <https://www.fuerthwiki.de/wiki/index.php?title=Attribut:UploadCommons> to True
* Maybe add an attribute that links directly to the file
