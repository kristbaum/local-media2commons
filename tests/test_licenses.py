import pytest

from media2commons.licenses import (
    MALFORMED,
    NO_LICENSE,
    is_commons_compatible,
    license_template,
    normalize_license,
    strip_markup,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("cc-by-sa-3.0", "CC-BY-SA-3.0"),
        ("CC-BY-SA-4.0", "CC-BY-SA-4.0"),
        ("cc-by-sa-3", "CC-BY-SA-3.0"),
        ("gemeinfrei", "Public Domain"),
        ("pd", "Public Domain"),
        ("gfdl", "GFDL"),
        ("copyright", "Copyright"),
        ("cc-by-nc-sa-3.0", "CC-BY-NC-SA-3.0"),
        ("bildlizenz-stadtarchiv", "Stadtarchiv License"),
    ],
)
def test_known_licenses_are_canonicalized(raw, expected):
    assert normalize_license(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_missing_license(raw):
    assert normalize_license(raw) == NO_LICENSE


def test_license_embedded_in_markup_is_extracted():
    raw = '<div class="license">[[Lizenz]] cc-by-sa-4.0 siehe dort</div>'
    assert normalize_license(raw) == "CC-BY-SA-4.0"


def test_long_prose_without_a_license_is_flagged():
    raw = "Diese Datei stammt aus einem Nachlass, die Rechtelage ist ungeklärt."
    assert normalize_license(raw) == MALFORMED


def test_long_prose_still_yields_a_license():
    raw = "Alle Rechte vorbehalten, das copyright liegt bei der Familie Müller."
    assert normalize_license(raw) == "Copyright"


def test_unknown_short_license_is_passed_through():
    assert normalize_license("Bildrechte Familie Müller") == "Bildrechte Familie Müller"


def test_strip_markup_removes_tags_links_and_tables():
    assert strip_markup("<b>a</b> [[link]]  b") == "a b"


@pytest.mark.parametrize(
    ("name", "compatible"),
    [
        ("CC-BY-SA-3.0", True),
        ("CC-BY-SA-4.0", True),
        ("Public Domain", True),
        ("GFDL", True),
        ("CC-BY-NC-3.0", False),
        ("Copyright", False),
        (NO_LICENSE, False),
        (None, False),
    ],
)
def test_commons_compatibility(name, compatible):
    assert is_commons_compatible(name) is compatible


def test_every_compatible_license_has_a_template():
    for name in ["CC-BY-SA-3.0", "CC-BY-SA-4.0", "CC-BY-3.0", "Public Domain", "GFDL"]:
        assert license_template(name)


def test_incompatible_license_has_no_template():
    assert license_template("Copyright") is None
