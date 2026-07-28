from helpers import step3_row

from media2commons.transform import (
    COMMONS_READY_FIELDS,
    to_commons_row,
    transform_rows,
)

ON_COMMONS = "https://commons.wikimedia.org/wiki/File:X.jpg"


def test_compatible_row_is_transformed():
    row = to_commons_row(step3_row(), year=2025)

    assert row is not None
    assert set(row) == set(COMMONS_READY_FIELDS)
    assert row["commons_filename"] == "Rathaus.jpg"
    assert row["original_title"] == "Datei:Rathaus.jpg"
    assert row["license"] == "CC-BY-SA-3.0"
    assert row["date"] == "1950"
    assert row["author"] == "Someone"
    assert row["description"] == "Das Rathaus von Fürth"
    assert "{{self|CC-BY-SA-3.0}}" in row["wikitext"]


def test_files_already_on_commons_are_skipped():
    assert to_commons_row(step3_row(commons_url=ON_COMMONS)) is None
    # A result file written before the column held a URL.
    assert to_commons_row(step3_row(exists_on_commons="True")) is None


def test_incompatible_licenses_are_skipped():
    for license_value in ["copyright", "cc-by-nc-3.0", "bildlizenz-stadtarchiv", ""]:
        assert to_commons_row(step3_row(Lizenz=license_value)) is None


def test_public_domain_row_is_kept():
    row = to_commons_row(step3_row(Lizenz="gemeinfrei"))

    assert row is not None
    assert row["license"] == "Public Domain"
    assert "{{PD-self}}" in row["wikitext"]


def test_missing_metadata_produces_empty_fields():
    row = to_commons_row(
        step3_row(Beschreibung="", Urheber="", Quellangaben="", Erstellungsdatum="")
    )

    assert row is not None
    assert row["description"] == ""
    assert row["author"] == ""
    assert row["date"] == ""
    assert "|date=\n" in row["wikitext"]


def test_transform_rows_filters_the_stream():
    rows = [
        step3_row(title="Datei:A.jpg"),
        step3_row(title="Datei:B.jpg", Lizenz="copyright"),
        step3_row(title="Datei:C.jpg", commons_url=ON_COMMONS),
        step3_row(title="Datei:D.jpg", Lizenz="cc-by-sa-4.0"),
    ]

    result = list(transform_rows(rows))

    assert [row["commons_filename"] for row in result] == ["A.jpg", "D.jpg"]
