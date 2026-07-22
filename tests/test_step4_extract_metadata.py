from media2commons.steps.step4_extract_metadata import (
    chunked,
    extract_metadata,
    format_property_values,
    metadata_row,
    output_fields,
)

PROPERTIES = ["Beschreibung", "Erstellungsdatum", "Lizenz"]


def ask_response(results):
    return {"query": {"results": results}}


def test_chunked_splits_evenly_and_keeps_the_remainder():
    assert list(chunked(list(range(5)), 2)) == [[0, 1], [2, 3], [4]]


def test_date_properties_are_normalized():
    values = [{"raw": "1/1754/8/12", "timestamp": "..."}]
    assert format_property_values("Erstellungsdatum", values) == "1754-08-12"


def test_multiple_values_are_joined():
    assert format_property_values("Person", ["Anna", "Bert"]) == "Anna; Bert"


def test_missing_values_become_empty_cells():
    assert format_property_values("Lizenz", []) == ""


def test_metadata_row_merges_into_the_input_row():
    base = {"title": "Datei:A.jpg", "sha1": "a", "url": "u"}
    entry = {"printouts": {"Beschreibung": ["Ein Bild"], "Lizenz": ["cc-by-sa-3.0"]}}

    row = metadata_row(base, entry, PROPERTIES)

    assert row["title"] == "Datei:A.jpg"
    assert row["Beschreibung"] == "Ein Bild"
    assert row["Lizenz"] == "cc-by-sa-3.0"
    assert row["Erstellungsdatum"] == ""


def test_extract_metadata_batches_titles(fake_session, fake_response):
    rows = [{"title": f"Datei:{i}.jpg", "sha1": str(i), "url": "u"} for i in range(3)]
    session = fake_session(
        [
            fake_response(
                ask_response({"Datei:0.jpg": {"printouts": {"Lizenz": ["pd"]}}})
            ),
            fake_response(
                ask_response({"Datei:2.jpg": {"printouts": {"Lizenz": ["gfdl"]}}})
            ),
        ]
    )

    results = extract_metadata(session, rows, PROPERTIES, chunk_size=2)

    assert len(session.calls) == 2
    assert "[[Datei:0.jpg]] OR [[Datei:1.jpg]]" in session.calls[0]["params"]["query"]
    assert "|?Lizenz" in session.calls[0]["params"]["query"]
    # Only titles the wiki returned metadata for end up in the output.
    assert [row["title"] for row in results] == ["Datei:0.jpg", "Datei:2.jpg"]


def test_output_fields_appends_new_properties_only():
    rows = [{"title": "t", "sha1": "s", "url": "u", "Lizenz": "x"}]
    assert output_fields(rows, PROPERTIES) == [
        "title",
        "sha1",
        "url",
        "Lizenz",
        "Beschreibung",
        "Erstellungsdatum",
    ]


def test_output_fields_without_rows_falls_back_to_defaults():
    assert output_fields([], PROPERTIES) == ["title", "sha1", "url", *PROPERTIES]
