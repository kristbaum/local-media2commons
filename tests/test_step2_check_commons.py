import pytest
from helpers import FakeResponse

from media2commons.csv_io import read_rows, write_rows
from media2commons.steps.step2_check_commons import (
    check_files,
    rows_already_done,
)

INPUT_FIELDS = ["title", "sha1", "url"]


@pytest.fixture
def input_csv(tmp_path):
    path = tmp_path / "step1.csv"
    write_rows(
        path,
        [
            {"title": f"Datei:{i}.jpg", "sha1": f"hash{i}", "url": f"u{i}"}
            for i in range(3)
        ],
        INPUT_FIELDS,
    )
    return path


def found(sha1s):
    """Response factory: report a match only for the given hashes."""

    def respond(url, params):
        images = [{"name": "x"}] if params["aisha1"] in sha1s else []
        return FakeResponse({"query": {"allimages": images}})

    return respond


def test_each_row_gets_a_verdict(tmp_path, input_csv, fake_session):
    output = tmp_path / "step2.csv"
    session = fake_session([found({"hash1"})] * 3)

    processed = check_files(session, input_csv, output, delay=0)

    assert processed == 3
    assert [row["exists_on_commons"] for row in read_rows(output)] == [
        "False",
        "True",
        "False",
    ]


def test_skip_and_limit_select_a_window(tmp_path, input_csv, fake_session):
    output = tmp_path / "step2.csv"
    session = fake_session([found(set())] * 3)

    processed = check_files(session, input_csv, output, skip=1, limit=1, delay=0)

    assert processed == 1
    assert [row["sha1"] for row in read_rows(output)] == ["hash1"]


def test_failed_lookups_are_not_written(tmp_path, input_csv, fake_session):
    def boom(url, params):
        raise RuntimeError("API is down")

    output = tmp_path / "step2.csv"
    session = fake_session([found(set()), boom, found(set())])

    processed = check_files(session, input_csv, output, delay=0)

    assert processed == 2
    assert [row["sha1"] for row in read_rows(output)] == ["hash0", "hash2"]


def test_step1_commons_columns_are_passed_through(tmp_path, fake_session):
    input_path = tmp_path / "step1.csv"
    write_rows(
        input_path,
        [
            {
                "title": "Datei:0.jpg",
                "sha1": "hash0",
                "url": "u0",
                "UploadCommons": "False",
                "CommonsLink": "https://commons.wikimedia.org/wiki/File:0.jpg",
            }
        ],
        [*INPUT_FIELDS, "UploadCommons", "CommonsLink"],
    )
    output = tmp_path / "step2.csv"

    check_files(fake_session([found(set())]), input_path, output, delay=0)

    row = read_rows(output)[0]
    assert row["UploadCommons"] == "False"
    assert row["CommonsLink"].endswith("File:0.jpg")


def test_rows_already_done_counts_partial_output(tmp_path, input_csv, fake_session):
    output = tmp_path / "step2.csv"
    assert rows_already_done(output) == 0

    check_files(fake_session([found(set())]), input_csv, output, limit=1, delay=0)
    assert rows_already_done(output) == 1


def test_resuming_continues_where_it_stopped(tmp_path, input_csv, fake_session):
    output = tmp_path / "step2.csv"
    check_files(fake_session([found(set())]), input_csv, output, limit=1, delay=0)

    check_files(
        fake_session([found(set())] * 2),
        input_csv,
        output,
        skip=rows_already_done(output),
        delay=0,
    )

    assert [row["sha1"] for row in read_rows(output)] == ["hash0", "hash1", "hash2"]
