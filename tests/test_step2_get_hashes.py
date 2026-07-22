from media2commons.csv_io import read_rows, write_rows
from media2commons.steps.step2_get_hashes import FIELDS, collect_hashes, image_row


def page(images, cont=None):
    payload = {"query": {"allimages": images}}
    if cont:
        payload["continue"] = {"aicontinue": cont}
    return payload


def test_image_row_builds_page_url():
    row = image_row({"title": "Datei:Altes Rathaus.jpg", "sha1": "abc"})

    assert row["sha1"] == "abc"
    assert row["url"].endswith("Datei:Altes_Rathaus.jpg")


def test_collect_hashes_follows_continuation(fake_session, fake_response):
    session = fake_session(
        [
            fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}], cont="A|B")),
            fake_response(page([{"title": "Datei:B.jpg", "sha1": "b"}])),
        ]
    )

    rows = collect_hashes(session, "https://wiki.example/api.php")

    assert [row["sha1"] for row in rows] == ["a", "b"]
    assert "aicontinue" not in session.calls[0]["params"]
    assert session.calls[1]["params"]["aicontinue"] == "A|B"


def test_collect_hashes_handles_empty_wiki(fake_session, fake_response):
    session = fake_session([fake_response(page([]))])
    assert collect_hashes(session, "https://wiki.example/api.php") == []


def test_rows_are_written_with_the_expected_columns(
    tmp_path, fake_session, fake_response
):
    session = fake_session(
        [fake_response(page([{"title": "Datei:A.jpg", "sha1": "a"}]))]
    )
    path = tmp_path / "step2.csv"

    write_rows(path, collect_hashes(session, "https://wiki.example/api.php"), FIELDS)

    assert list(read_rows(path)[0]) == FIELDS
