from media2commons.csv_io import read_rows, write_rows
from media2commons.steps.step1_get_hashes import FIELDS, collect_hashes, image_row

PROPERTIES = ["UploadCommons", "CommonsLink"]


def page(images, cont=None):
    payload = {"query": {"allimages": images}}
    if cont:
        payload["continue"] = {"aicontinue": cont}
    return payload


# Shaped like a real FürthWiki ASK response: a boolean printout is declared as
# `_boo` and answered with "t"/"f", and an empty result set is a list, not a map.
PRINTREQUESTS = [
    {"label": "UploadCommons", "typeid": "_boo"},
    {"label": "CommonsLink", "typeid": "_txt"},
]


def ask_page(results):
    return {"query": {"printrequests": PRINTREQUESTS, "results": results}}


def smw_entry(upload_commons, commons_link=""):
    return {
        "printouts": {
            "UploadCommons": [upload_commons],
            "CommonsLink": [commons_link] if commons_link else [],
        }
    }


def test_image_row_builds_page_url():
    row = image_row({"title": "Datei:Altes Rathaus.jpg", "sha1": "abc"})

    assert row["sha1"] == "abc"
    assert row["url"].endswith("Datei:Altes_Rathaus.jpg")


def test_image_row_leaves_commons_columns_empty_without_smw_data():
    row = image_row({"title": "Datei:A.jpg", "sha1": "a"})

    assert row["UploadCommons"] == ""
    assert row["CommonsLink"] == ""


def test_collect_hashes_follows_continuation(fake_session, fake_response):
    session = fake_session(
        [
            fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}], cont="A|B")),
            fake_response(page([{"title": "Datei:B.jpg", "sha1": "b"}])),
        ]
    )

    rows = collect_hashes(session, "https://wiki.example/api.php", properties=[])

    assert [row["sha1"] for row in rows] == ["a", "b"]
    assert "aicontinue" not in session.calls[0]["params"]
    assert session.calls[1]["params"]["aicontinue"] == "A|B"


def test_collect_hashes_handles_empty_wiki(fake_session, fake_response):
    session = fake_session([fake_response(page([]))])
    assert collect_hashes(session, "https://wiki.example/api.php", properties=[]) == []


def test_collect_hashes_merges_smw_commons_status(fake_session, fake_response):
    session = fake_session(
        [
            fake_response(
                ask_page(
                    {
                        "Datei:A.jpg": smw_entry(
                            "f", "https://commons.wikimedia.org/wiki/File:A.jpg"
                        )
                    }
                )
            ),
            fake_response(
                page(
                    [
                        {"title": "Datei:A.jpg", "sha1": "a"},
                        {"title": "Datei:B.jpg", "sha1": "b"},
                    ]
                )
            ),
        ]
    )

    rows = collect_hashes(session, "https://wiki.example/api.php", PROPERTIES)

    assert rows[0]["UploadCommons"] == "False"
    assert rows[0]["CommonsLink"].endswith("File:A.jpg")
    # A file the wiki says nothing about keeps both columns empty.
    assert rows[1]["UploadCommons"] == ""
    assert rows[1]["CommonsLink"] == ""


def test_no_page_carries_the_properties(fake_session, fake_response):
    """SMW answers a query without matches with an empty list, not an object."""
    session = fake_session(
        [
            fake_response({"query": {"printrequests": PRINTREQUESTS, "results": []}}),
            fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}])),
        ]
    )

    rows = collect_hashes(session, "https://wiki.example/api.php", PROPERTIES)

    assert rows[0]["UploadCommons"] == ""
    assert rows[0]["CommonsLink"] == ""


def test_commons_status_is_asked_by_property_not_by_title(fake_session, fake_response):
    session = fake_session(
        [
            fake_response(ask_page({})),
            fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}])),
        ]
    )

    collect_hashes(session, "https://wiki.example/api.php", PROPERTIES)

    query = session.calls[0]["params"]["query"]
    assert query.startswith("[[UploadCommons::+]] OR [[CommonsLink::+]]")
    assert "|?UploadCommons|?CommonsLink" in query
    assert "Datei:A.jpg" not in query


def test_commons_status_pages_until_a_short_page(fake_session, fake_response):
    full_page = ask_page(
        {f"Datei:{index}.jpg": smw_entry("t") for index in range(500)}
    )
    session = fake_session(
        [
            fake_response(full_page),
            fake_response(ask_page({"Datei:Last.jpg": smw_entry("t")})),
            fake_response(page([{"title": "Datei:Last.jpg", "sha1": "z"}])),
        ]
    )

    rows = collect_hashes(session, "https://wiki.example/api.php", PROPERTIES)

    assert "offset=0" in session.calls[0]["params"]["query"]
    assert "offset=500" in session.calls[1]["params"]["query"]
    assert rows[0]["UploadCommons"] == "True"


def test_repeated_ask_page_does_not_loop_forever(fake_session, fake_response):
    """A wiki that ignores `offset` must not keep the run spinning."""
    full_page = ask_page(
        {f"Datei:{index}.jpg": smw_entry("t") for index in range(500)}
    )
    session = fake_session(
        [
            fake_response(full_page),
            fake_response(full_page),
            fake_response(page([])),
        ]
    )

    assert collect_hashes(session, "https://wiki.example/api.php", PROPERTIES) == []


def test_rows_are_written_with_the_expected_columns(
    tmp_path, fake_session, fake_response
):
    session = fake_session(
        [fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}]))]
    )
    path = tmp_path / "step1.csv"

    write_rows(
        path,
        collect_hashes(session, "https://wiki.example/api.php", properties=[]),
        FIELDS,
    )

    assert list(read_rows(path)[0]) == FIELDS
    assert FIELDS == ["title", "sha1", "url", "UploadCommons", "CommonsLink"]
