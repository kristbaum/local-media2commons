import pytest

from media2commons.wikitext import (
    build_wikitext,
    clean_author,
    clean_description,
    clean_filename,
    clean_source,
    unlink,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("[[Rathaus]]", "Rathaus"),
        ("[[Rathaus|das Rathaus]]", "das Rathaus"),
        ("vor dem [[Rathaus|Rathaus]] in [[Fürth]]", "vor dem Rathaus in Fürth"),
        ("kein Link", "kein Link"),
    ],
)
def test_unlink(raw, expected):
    assert unlink(raw) == expected


def test_clean_filename_strips_local_namespace():
    assert clean_filename("Datei:Rathaus.jpg") == "Rathaus.jpg"
    assert clean_filename("Rathaus.jpg") == "Rathaus.jpg"


def test_clean_description_fixes_doubled_quotes():
    assert clean_description('Das ""alte"" Rathaus') == 'Das "alte" Rathaus'


def test_clean_author_drops_user_prefix():
    assert clean_author("[[Benutzer:Someone|Someone]]") == "Someone"
    assert clean_author("Benutzer:Someone") == "Someone"


@pytest.mark.parametrize("cleaner", [clean_description, clean_author, clean_source])
def test_cleaners_handle_empty_input(cleaner):
    assert cleaner("") == ""
    assert cleaner(None) == ""


def test_build_wikitext_contains_all_sections():
    text = build_wikitext(
        description="Das Rathaus",
        date="1950",
        source="Stadtarchiv",
        author="Someone",
        source_url="https://www.fuerthwiki.de/wiki/index.php/Datei:Rathaus.jpg",
        license_name="CC-BY-SA-3.0",
        year=2025,
    )

    assert "=={{int:filedesc}}==" in text
    assert "{{Information" in text
    assert "|description={{de|1=Das Rathaus}}" in text
    assert "|date=1950" in text
    assert "|author=Someone" in text
    assert "FürthWiki] - Stadtarchiv" in text
    assert "=={{int:license-header}}==" in text
    assert "{{self|CC-BY-SA-3.0}}" in text
    assert "[[Category:Images from FürthWiki]]" in text
    assert "[[Category:Media uploaded from FürthWiki (2025)]]" in text


def test_build_wikitext_without_source_still_links_back():
    text = build_wikitext(
        description="d",
        date="",
        source="",
        author="",
        source_url="https://example.org/file",
        license_name="Public Domain",
        year=2025,
    )

    assert "|source=[https://example.org/file FürthWiki]\n" in text
    assert "{{PD-self}}" in text


def test_build_wikitext_rejects_incompatible_license():
    with pytest.raises(ValueError):
        build_wikitext(
            description="d",
            date="",
            source="",
            author="",
            source_url="u",
            license_name="Copyright",
        )
