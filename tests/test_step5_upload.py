import hashlib

import pytest
from helpers import FakeResponse

from media2commons.csv_io import read_rows
from media2commons.downloader import (
    download_file,
    fetch_file_url,
    file_sha1,
    find_file_url,
    safe_local_name,
    verify_sha1,
)
from media2commons.upload_batch import BatchSummary, process_row, run_batch
from media2commons.uploader import CommonsUploader, UploadLog, UploadResult

FILE_PAGE_HTML = """
<div class="fullImageLink">
  <a href="/wiki/images/thumb/a/ab/Rathaus.jpg/220px-Rathaus.jpg">thumb</a>
  <a href="/wiki/images/a/ab/Rathaus.jpg">Original</a>
</div>
"""

CONTENT = b"a tiny jpeg"
CONTENT_SHA1 = hashlib.sha1(CONTENT).hexdigest()


def test_find_file_url_prefers_the_original_over_thumbnails():
    url = find_file_url(FILE_PAGE_HTML)
    assert url == "https://www.fuerthwiki.de/wiki/images/a/ab/Rathaus.jpg"


def test_find_file_url_returns_none_when_absent():
    assert find_file_url("<p>Diese Datei wurde gelöscht.</p>") is None


def test_fetch_file_url_reads_the_page(fake_session):
    session = fake_session([FakeResponse(text=FILE_PAGE_HTML)])
    assert fetch_file_url(session, "https://wiki.example/File:Rathaus.jpg")


def test_safe_local_name_drops_problematic_characters():
    assert safe_local_name("Rathaus/../etc.jpg") == "Rathaus..etc.jpg"
    assert "/" not in safe_local_name("a/b.jpg")


def test_file_sha1_matches_hashlib(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(CONTENT)
    assert file_sha1(path) == CONTENT_SHA1


def test_verify_sha1_is_case_insensitive_and_rejects_empty(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(CONTENT)

    assert verify_sha1(path, CONTENT_SHA1.upper())
    assert not verify_sha1(path, "deadbeef")
    assert not verify_sha1(path, "")


def test_download_verifies_the_hash(tmp_path, fake_session):
    session = fake_session([FakeResponse(content=CONTENT)])
    destination = tmp_path / "Rathaus.jpg"

    result = download_file(session, "https://wiki/f.jpg", destination, CONTENT_SHA1)

    assert result == destination
    assert destination.read_bytes() == CONTENT


def test_corrupted_download_is_deleted(tmp_path, fake_session):
    session = fake_session([FakeResponse(content=b"wrong bytes")])
    destination = tmp_path / "Rathaus.jpg"

    assert download_file(session, "https://wiki/f.jpg", destination, CONTENT_SHA1) is None
    assert not destination.exists()


def test_existing_verified_file_is_not_downloaded_again(tmp_path, fake_session):
    destination = tmp_path / "Rathaus.jpg"
    destination.write_bytes(CONTENT)
    session = fake_session([])  # any request would raise

    assert download_file(session, "https://wiki/f.jpg", destination, CONTENT_SHA1)


def test_existing_file_with_wrong_hash_is_replaced(tmp_path, fake_session):
    destination = tmp_path / "Rathaus.jpg"
    destination.write_bytes(b"stale")
    session = fake_session([FakeResponse(content=CONTENT)])

    assert download_file(session, "https://wiki/f.jpg", destination, CONTENT_SHA1)
    assert destination.read_bytes() == CONTENT


class FakePage:
    def __init__(self, exists=False):
        self.exists = exists


class FakePages(dict):
    """``site.pages[...]`` returns a non-existing page for unknown titles."""

    def __getitem__(self, key):
        return self.get(key, FakePage(False))


class FakeSite:
    """Stand-in for :class:`mwclient.Site`."""

    def __init__(self, existing=(), upload_result=None, upload_error=None):
        self.pages = FakePages({f"File:{name}": FakePage(True) for name in existing})
        self._upload_result = upload_result or {"result": "Success"}
        self._upload_error = upload_error
        self.uploads = []
        self.logged_in_as = None

    def login(self, username, password):
        self.logged_in_as = username

    def upload(self, file, filename, description, comment):
        if self._upload_error:
            raise self._upload_error
        self.uploads.append({"filename": filename, "description": description})
        return self._upload_result


@pytest.fixture
def site_factory():
    return FakeSite


def test_successful_upload(tmp_path, site_factory):
    path = tmp_path / "Rathaus.jpg"
    path.write_bytes(CONTENT)
    site = site_factory()
    uploader = CommonsUploader("bot", "pw", site=site)

    result = uploader.upload(path, "Rathaus.jpg", "wikitext")

    assert result.uploaded
    assert result.commons_url.endswith("File:Rathaus.jpg")
    assert site.uploads[0]["description"] == "wikitext"


def test_existing_commons_file_is_not_reuploaded(tmp_path, site_factory):
    path = tmp_path / "Rathaus.jpg"
    path.write_bytes(CONTENT)
    site = site_factory(existing=["Rathaus.jpg"])
    uploader = CommonsUploader("bot", "pw", site=site)

    result = uploader.upload(path, "Rathaus.jpg", "wikitext")

    assert result.status == "exists"
    assert not site.uploads


def test_api_warning_is_reported_as_failure(tmp_path, site_factory):
    path = tmp_path / "Rathaus.jpg"
    path.write_bytes(CONTENT)
    site = site_factory(upload_result={"result": "Warning", "warnings": {"exists": 1}})
    uploader = CommonsUploader("bot", "pw", site=site)

    result = uploader.upload(path, "Rathaus.jpg", "wikitext")

    assert result.status == "failed"
    assert "exists" in result.error_message


def test_upload_exception_becomes_an_error_result(tmp_path, site_factory):
    path = tmp_path / "Rathaus.jpg"
    path.write_bytes(CONTENT)
    site = site_factory(upload_error=RuntimeError("abuse filter"))
    uploader = CommonsUploader("bot", "pw", site=site)

    result = uploader.upload(path, "Rathaus.jpg", "wikitext")

    assert result.status == "error"
    assert "abuse filter" in result.error_message


def test_upload_without_connection_errors(tmp_path):
    uploader = CommonsUploader("bot", "pw")
    result = uploader.upload(tmp_path / "missing.jpg", "Rathaus.jpg", "w")
    assert result.status == "error"


def test_upload_log_appends_rows(tmp_path):
    log = UploadLog(tmp_path / "log.csv")

    log.record("A.jpg", "success", "https://commons/A.jpg")
    log.record("B.jpg", "error", "", "boom")

    rows = read_rows(tmp_path / "log.csv")
    assert [row["status"] for row in rows] == ["success", "error"]
    assert rows[1]["error_message"] == "boom"


def commons_row(**overrides):
    row = {
        "commons_filename": "Rathaus.jpg",
        "fuerthwiki_url": "https://wiki/File:Rathaus.jpg",
        "sha1": CONTENT_SHA1,
        "wikitext": "wikitext",
    }
    row.update(overrides)
    return row


def test_process_row_downloads_then_uploads(tmp_path, fake_session, site_factory):
    session = fake_session(
        [FakeResponse(text=FILE_PAGE_HTML), FakeResponse(content=CONTENT)]
    )
    uploader = CommonsUploader("bot", "pw", site=site_factory())

    result = process_row(commons_row(), session, uploader, tmp_path)

    assert result.uploaded


def test_process_row_stops_when_the_file_url_is_missing(
    tmp_path, fake_session, site_factory
):
    session = fake_session([FakeResponse(text="<p>nichts</p>")])
    uploader = CommonsUploader("bot", "pw", site=site_factory())

    result = process_row(commons_row(), session, uploader, tmp_path)

    assert result.status == "no_url"


def test_process_row_stops_on_hash_mismatch(tmp_path, fake_session, site_factory):
    session = fake_session(
        [FakeResponse(text=FILE_PAGE_HTML), FakeResponse(content=b"tampered")]
    )
    site = site_factory()
    uploader = CommonsUploader("bot", "pw", site=site)

    result = process_row(commons_row(), session, uploader, tmp_path)

    assert result.status == "download_failed"
    assert not site.uploads


def test_run_batch_logs_every_row(tmp_path, fake_session, site_factory):
    session = fake_session(
        [
            FakeResponse(text=FILE_PAGE_HTML),
            FakeResponse(content=CONTENT),
            FakeResponse(text="<p>nichts</p>"),
        ]
    )
    log = UploadLog(tmp_path / "log.csv")
    rows = [commons_row(), commons_row(commons_filename="Gone.jpg")]

    summary = run_batch(
        rows,
        session,
        CommonsUploader("bot", "pw", site=site_factory()),
        log,
        download_dir=tmp_path,
        delay=0,
    )

    assert summary.processed == 2
    assert summary.uploaded == 1
    assert summary.failed == 1
    assert [row["status"] for row in read_rows(tmp_path / "log.csv")] == [
        "success",
        "no_url",
    ]


def test_batch_summary_counts_categories():
    summary = BatchSummary()
    summary.record(UploadResult("success"))
    summary.record(UploadResult("exists"))
    summary.record(UploadResult("error"))

    assert (summary.uploaded, summary.skipped, summary.failed) == (1, 1, 1)
    assert summary.success_rate == pytest.approx(33.3, abs=0.1)


def test_empty_batch_summary_has_no_success_rate():
    assert BatchSummary().success_rate == 0.0
