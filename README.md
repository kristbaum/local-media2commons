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
| 2. List files + hashes | `uv run m2c-step2-hashes` | local wiki API | `data/step2_result.csv` |
| 3. Check against Commons | `uv run m2c-step3-commons-check` | `step2_result.csv` | `data/step3_result.csv` |
| 4. Extract SMW metadata | `uv run m2c-step4-metadata` | `step3_result.csv` | `data/step4_result.csv` |
| 4b. Analysis report | `uv run m2c-step4-report` | `step4_result.csv` | `data/step4_report.txt` |
| 5. Transform for Commons | `uv run m2c-step5-transform` | `step4_result.csv` | `data/step5_commons_ready.csv` |
| 6. Upload | `uv run m2c-step6-upload` | `step5_commons_ready.csv` | `data/step6_upload_log.csv` |

Step 1 — getting a list of files out of the local MediaWiki — is covered by step 2,
which queries the API directly. Every step takes `--input`/`--output` overrides; run any
of them with `--help` for the full set of options.

### Step 2 — collect file hashes

Pages through the `list=allimages` API of the local wiki with `aiprop=sha1`, following
continuation until every file is listed, and records title, SHA-1 and file page URL.

### Step 3 — check what is already on Commons

Looks each SHA-1 up via `list=allimages&aisha1=…` on Commons; a non-empty result means
the identical file is already there. This is the long-running step (one request per
file, throttled by `--delay`), so results are appended row by row and an interrupted run
resumes automatically after the rows already in the output file. Use `--skip`/`--limit`
to process an explicit window.

```text
https://commons.wikimedia.org/w/api.php?action=query&list=allimages&aisha1=fcdfc17fac0c39e6f201f2022f9f1f9f8b35d449&format=json
```

### Step 4 — extract metadata

Queries the Semantic MediaWiki ASK API in batches of 10 titles for the properties
`Beschreibung`, `Erstellungsdatum`, `Erstellungsjahr`, `Lizenz`, `Person`,
`Quellangaben` and `Urheber`. SMW's raw date format (`1/1754/8/12`) is normalised to
`YYYY`, `YYYY-MM` or `YYYY-MM-DD`. Only files SMW returns metadata for reach the output.

The companion report step summarises license distribution, creation years and metadata
completeness, and estimates how many files are actually uploadable.

### Step 5 — transform for Commons

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

### Step 6 — upload

For each prepared row: resolve the original (non-thumbnail) file URL from its wiki page,
download it, verify the SHA-1 against the hash recorded in step 2, and upload it to
Commons via `mwclient`. Files whose hash does not match are never uploaded, and a file
that already exists on Commons is skipped. Every attempt is logged to
`data/step6_upload_log.csv`.

Credentials are read from `COMMONS_USERNAME` and `COMMONS_PASSWORD` (use a
[bot password](https://commons.wikimedia.org/wiki/Special:BotPasswords)) and prompted for
otherwise. The run asks for confirmation unless `--yes` is given. Start small:

```bash
COMMONS_USERNAME=YourBot COMMONS_PASSWORD=… uv run m2c-step6-upload --max-files 5
```

## Project layout

```text
src/media2commons/
  config.py        endpoints, SMW properties, file paths
  csv_io.py        CSV read/write/append helpers
  mediawiki.py     MediaWiki + SMW API access
  licenses.py      license normalisation and Commons compatibility
  dates.py         SMW date parsing and year extraction
  wikitext.py      Commons file description page rendering
  transform.py     step 4 rows -> upload-ready rows
  analysis.py      statistics over the metadata dump
  reporting.py     text rendering of those statistics
  downloader.py    file URL resolution, download, SHA-1 verification
  uploader.py      Commons login, upload, upload log
  upload_batch.py  per-file and batch orchestration for step 6
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
