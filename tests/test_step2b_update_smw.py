import pytest
from helpers import FakeResponse

from media2commons.csv_io import read_rows
from media2commons.smw_update import (
    UpdateLog,
    rows_to_update,
    run_updates,
    update_page,
)

API = "https://www.fuerthwiki.de/wiki/api.php"
COMMONS_URL = "https://commons.wikimedia.org/wiki/File:Rathaus_von_F%C3%BCrth.jpg"

BILD = "{{Bild\n|Genre=Fotografien\n|UploadCommons=Nein\n|Lizenz=cc-by-sa-3.0\n}}"


def revision(text):
    """An ``action=query&prop=revisions`` reply carrying `text`."""
    return FakeResponse(
        {
            "query": {
                "pages": [
                    {
                        "title": "Datei:Rathaus.jpg",
                        "revisions": [
                            {
                                "timestamp": "2026-07-01T10:00:00Z",
                                "slots": {"main": {"content": text}},
                            }
                        ],
                    }
                ]
            }
        }
    )


MISSING = FakeResponse(
    {"query": {"pages": [{"title": "Datei:X.jpg", "missing": True}]}}
)
SAVED = FakeResponse({"edit": {"result": "Success"}})


def step2_row(**overrides):
    row = {"title": "Datei:Rathaus.jpg", "sha1": "abc", "commons_url": COMMONS_URL}
    row.update(overrides)
    return row


def test_the_page_is_saved_with_both_properties_set(fake_session):
    session = fake_session([revision(BILD), SAVED])

    result = update_page(session, "Datei:Rathaus.jpg", COMMONS_URL, "tok", API)

    assert result.status == "updated"
    assert result.commons_filename == "Rathaus von Fürth.jpg"
    edit = session.calls[1]["params"]
    assert "|UploadCommons=Ja\n" in edit["text"]
    assert "|CommonsLink=Rathaus von Fürth.jpg\n" in edit["text"]
    assert edit["token"] == "tok"
    # The revision the text was built from, so a concurrent edit is not lost.
    assert edit["basetimestamp"] == "2026-07-01T10:00:00Z"


def test_a_page_already_saying_so_is_not_saved_again(fake_session):
    settled = BILD.replace("UploadCommons=Nein", "UploadCommons=Ja").replace(
        "|Lizenz", "|CommonsLink=Rathaus von Fürth.jpg\n|Lizenz"
    )
    session = fake_session([revision(settled)])

    result = update_page(session, "Datei:Rathaus.jpg", COMMONS_URL, "tok", API)

    assert result.status == "unchanged"
    assert len(session.calls) == 1


def test_a_dry_run_never_saves(fake_session):
    session = fake_session([revision(BILD)])

    result = update_page(
        session, "Datei:Rathaus.jpg", COMMONS_URL, "tok", API, dry_run=True
    )

    assert result.status == "would-update"
    assert len(session.calls) == 1


def test_a_file_page_that_does_not_exist_is_reported(fake_session):
    session = fake_session([MISSING])

    result = update_page(session, "Datei:X.jpg", COMMONS_URL, "tok", API)

    assert result.status == "no-page"


def test_a_page_without_a_form_template_is_reported(fake_session):
    session = fake_session([revision("Nur Text, keine Vorlage.")])

    result = update_page(session, "Datei:X.jpg", COMMONS_URL, "tok", API)

    assert result.status == "no-template"


def test_an_unusable_commons_url_is_an_error(fake_session):
    session = fake_session([])

    result = update_page(session, "Datei:X.jpg", "https://example.org/", "tok", API)

    assert result.status == "error"


def test_an_api_error_on_saving_is_raised(fake_session):
    refused = FakeResponse({"error": {"code": "protectedpage", "info": "Protected."}})
    session = fake_session([revision(BILD), refused])

    with pytest.raises(RuntimeError, match="protectedpage"):
        update_page(session, "Datei:Rathaus.jpg", COMMONS_URL, "tok", API)


def test_only_rows_with_a_commons_url_are_visited():
    rows = [
        step2_row(title="Datei:A.jpg"),
        step2_row(title="Datei:B.jpg", commons_url=""),
        step2_row(title="Datei:C.jpg"),
    ]

    assert [row["title"] for row in rows_to_update(rows)] == [
        "Datei:A.jpg",
        "Datei:C.jpg",
    ]


def test_pages_settled_by_an_earlier_run_are_skipped():
    rows = [step2_row(title="Datei:A.jpg"), step2_row(title="Datei:B.jpg")]

    remaining = rows_to_update(rows, {"Datei:A.jpg"})

    assert [row["title"] for row in remaining] == ["Datei:B.jpg"]


def test_a_run_logs_every_outcome_and_carries_on(tmp_path, fake_session):
    def boom(url, params):
        raise RuntimeError("wiki is down")

    log = UpdateLog(tmp_path / "log.csv")
    session = fake_session([revision(BILD), SAVED, boom, revision(BILD), SAVED])
    rows = [
        step2_row(title="Datei:A.jpg"),
        step2_row(title="Datei:B.jpg"),
        step2_row(title="Datei:C.jpg"),
    ]

    counts = run_updates(rows, session, "tok", log, api_url=API)

    assert counts == {"updated": 2, "error": 1}
    logged = read_rows(log.path)
    assert [row["status"] for row in logged] == ["updated", "error", "updated"]
    assert "wiki is down" in logged[1]["message"]


def test_a_resumed_run_reads_the_settled_titles_back(tmp_path, fake_session):
    log = UpdateLog(tmp_path / "log.csv")
    session = fake_session([revision(BILD), SAVED, revision(BILD)])

    run_updates([step2_row(title="Datei:A.jpg")], session, "tok", log, api_url=API)
    run_updates(
        [step2_row(title="Datei:B.jpg")], session, "tok", log, api_url=API, dry_run=True
    )

    assert log.settled_titles() == {"Datei:A.jpg", "Datei:B.jpg"}


def test_a_failed_page_is_retried_by_the_next_run(tmp_path, fake_session):
    def boom(url, params):
        raise RuntimeError("wiki is down")

    log = UpdateLog(tmp_path / "log.csv")
    run_updates([step2_row()], fake_session([boom]), "tok", log, api_url=API)

    assert log.settled_titles() == set()
