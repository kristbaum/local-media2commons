import pytest

from media2commons.dates import extract_year, normalize_smw_date, year_string


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1/1754", "1754"),
        ("1/1754/8", "1754-08"),
        ("1/1754/8/12", "1754-08-12"),
        ("1950", "1950"),
        ("1950/11", "1950-11"),
        ("1950/11/3", "1950-11-03"),
        ("1/1950/11/3/12/30", "1/1950/11/3/12/30"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_smw_date(raw, expected):
    assert normalize_smw_date(raw) == expected


def test_normalize_smw_date_strips_whitespace():
    assert normalize_smw_date("  1/1899/2  ") == "1899-02"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1950", 1950),
        ("1950-06", 1950),
        ("1950-06-01", 1950),
        ("1754", 1754),
        ("ca. 1971 aufgenommen", 1971),
        ("", None),
        (None, None),
        ("kein Datum", None),
        ("99", None),
        ("12345", None),
    ],
)
def test_extract_year(raw, expected):
    assert extract_year(raw) == expected


def test_implausible_years_are_rejected():
    assert extract_year("3021") is None


def test_year_string_uses_empty_instead_of_none():
    assert year_string("1950-06") == "1950"
    assert year_string("kein Datum") == ""
