from datetime import datetime

from helpers import step3_row

from media2commons.analysis import analyze_rows, row_is_on_commons
from media2commons.reporting import render_report, render_summary

ROWS = [
    step3_row(title="Datei:A.jpg", Lizenz="cc-by-sa-3.0", Erstellungsdatum="1950"),
    step3_row(title="Datei:B.jpg", Lizenz="cc-by-sa-3.0", Erstellungsdatum="1955"),
    step3_row(title="Datei:C.jpg", Lizenz="copyright", Erstellungsdatum="1962"),
    step3_row(
        title="Datei:D.jpg",
        Lizenz="",
        Erstellungsdatum="",
        Beschreibung="",
        Urheber="",
        Quellangaben="",
        exists_on_commons="True",
    ),
]


def test_row_is_on_commons_accepts_any_casing():
    assert row_is_on_commons({"exists_on_commons": "True"})
    assert row_is_on_commons({"exists_on_commons": "true"})
    assert not row_is_on_commons({"exists_on_commons": "False"})
    assert not row_is_on_commons({})


def test_totals():
    stats = analyze_rows(ROWS)

    assert stats.total_images == 4
    assert stats.exists_on_commons == 1
    assert stats.not_on_commons == 3


def test_license_and_compatibility_counts():
    stats = analyze_rows(ROWS)

    assert stats.licenses["CC-BY-SA-3.0"] == 2
    assert stats.licenses["Copyright"] == 1
    assert stats.licenses["No license specified"] == 1
    assert stats.commons_compatible == 2


def test_year_and_decade_buckets():
    stats = analyze_rows(ROWS)

    assert stats.images_with_year == 3
    assert stats.years[1950] == 1
    assert stats.decades[1950] == 2
    assert stats.decades[1960] == 1


def test_completeness_ignores_blank_cells():
    stats = analyze_rows(ROWS)

    assert stats.completeness["description"] == 3
    assert stats.completeness["author"] == 3
    assert stats.completeness["source"] == 3


def test_percent_is_safe_for_an_empty_dataset():
    stats = analyze_rows([])

    assert stats.total_images == 0
    assert stats.percent(0) == 0.0


def test_render_report_covers_every_section():
    text = render_report(analyze_rows(ROWS), now=datetime(2025, 1, 1))

    assert "FÜRTHWIKI MEDIA ANALYSIS REPORT" in text
    assert "Total images analyzed: 4" in text
    assert "✓ CC-BY-SA-3.0: 2 (50.0%)" in text
    assert "✗ Copyright: 1 (25.0%)" in text
    assert "Potential Commons uploads: ~2 images" in text
    assert "KEY INSIGHTS" in text


def test_render_report_handles_an_empty_dataset():
    text = render_report(analyze_rows([]), now=datetime(2025, 1, 1))
    assert "Total images analyzed: 0" in text


def test_render_summary_is_the_short_form():
    text = render_summary(analyze_rows(ROWS), now=datetime(2025, 1, 1))

    assert text.startswith("FürthWiki Media Analysis Summary")
    assert "Total images: 4" in text
    assert "On Commons: 1" in text
    assert "Metadata completeness:" in text
    assert text.endswith("\n")
