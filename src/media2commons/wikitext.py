"""Building the Commons file description page from local wiki metadata."""

from __future__ import annotations

import re
from datetime import datetime

from .config import COMMONS_CATEGORIES
from .licenses import license_template

_LINK_WITH_LABEL = re.compile(r"\[\[([^|\]]+)\|([^]]+)\]\]")
_PLAIN_LINK = re.compile(r"\[\[([^]]+)\]\]")

# Namespace prefix the local wiki uses for files.
FILE_NAMESPACE_PREFIX = "Datei:"


def unlink(text: str) -> str:
    """Replace wiki links with their visible text: ``[[a|b]]`` -> ``b``."""
    text = _LINK_WITH_LABEL.sub(r"\2", text)
    return _PLAIN_LINK.sub(r"\1", text)


def clean_filename(title: str) -> str:
    """Strip the local file namespace prefix from a page title."""
    if title.startswith(FILE_NAMESPACE_PREFIX):
        return title[len(FILE_NAMESPACE_PREFIX) :]
    return title


def clean_description(description: str | None) -> str:
    """Flatten wiki links and fix doubled quotes coming from CSV round-trips."""
    if not description:
        return ""
    return unlink(description).replace('""', '"').strip()


def clean_author(author: str | None) -> str:
    """Flatten wiki links and drop the local ``Benutzer:`` user prefix."""
    if not author:
        return ""
    author = unlink(author).replace("Benutzer:", "")
    return author.replace("[[", "").replace("]]", "").strip()


def clean_source(source: str | None) -> str:
    """Flatten wiki links in a source attribution."""
    if not source:
        return ""
    return unlink(source).strip()


def build_information_template(
    description: str, date: str, source: str, author: str, source_url: str
) -> str:
    """Render the ``{{Information}}`` block of a Commons file page."""
    source_field = f"[{source_url} FürthWiki]"
    if source:
        source_field = f"{source_field} - {source}"

    return (
        "{{Information\n"
        f"|description={{{{de|1={description}}}}}\n"
        f"|date={date}\n"
        f"|source={source_field}\n"
        f"|author={author}\n"
        "|permission=\n"
        "|other_versions=\n"
        "}}"
    )


def build_wikitext(
    *,
    description: str,
    date: str,
    source: str,
    author: str,
    source_url: str,
    license_name: str,
    year: int | None = None,
) -> str:
    """Render a complete Commons file description page.

    `year` only feeds the upload-batch category and defaults to the current year.
    """
    template = license_template(license_name)
    if template is None:
        raise ValueError(f"No Commons license template for {license_name!r}")

    info = build_information_template(description, date, source, author, source_url)
    upload_year = year if year is not None else datetime.now().year
    categories = "\n".join(
        f"[[Category:{name.format(year=upload_year)}]]" for name in COMMONS_CATEGORIES
    )

    return (
        "=={{int:filedesc}}==\n"
        f"{info}\n"
        "\n"
        "=={{int:license-header}}==\n"
        f"{template}\n"
        "\n"
        f"{categories}"
    )
