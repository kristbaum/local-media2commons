from media2commons.csv_io import append_row, iter_rows, read_rows, write_rows

FIELDS = ["title", "sha1"]


def test_write_then_read_roundtrip(tmp_path):
    path = tmp_path / "out.csv"
    rows = [
        {"title": "Datei:Ä.jpg", "sha1": "a1"},
        {"title": "Datei:B, comma.jpg", "sha1": "b2"},
    ]

    assert write_rows(path, rows, FIELDS) == 2
    assert read_rows(path) == rows


def test_write_rows_creates_missing_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "out.csv"
    write_rows(path, [{"title": "t", "sha1": "s"}], FIELDS)
    assert path.exists()


def test_iter_rows_streams_the_same_rows(tmp_path):
    path = tmp_path / "out.csv"
    write_rows(path, [{"title": f"t{i}", "sha1": str(i)} for i in range(5)], FIELDS)
    assert [row["title"] for row in iter_rows(path)] == [f"t{i}" for i in range(5)]


def test_append_row_writes_header_only_once(tmp_path):
    path = tmp_path / "out.csv"

    append_row(path, {"title": "a", "sha1": "1"}, FIELDS)
    append_row(path, {"title": "b", "sha1": "2"}, FIELDS)

    assert path.read_text(encoding="utf-8").count("title,sha1") == 1
    assert len(read_rows(path)) == 2
