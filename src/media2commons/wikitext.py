"""Reading and writing wikitext: Commons file pages, and the source wiki's forms."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from urllib.parse import unquote

from .config import COMMONS_CATEGORIES, FORM_TEMPLATES
from .licenses import license_template

_LINK_WITH_LABEL = re.compile(r"\[\[([^|\]]+)\|([^]]+)\]\]")
_PLAIN_LINK = re.compile(r"\[\[([^]]+)\]\]")

# Start of a template call, capturing its name.
_TEMPLATE_START = re.compile(r"\{\{\s*([^|{}\s][^|{}\n]*?)\s*(?=[|}\n])")

# Namespace prefix the local wiki uses for files.
FILE_NAMESPACE_PREFIX = "Datei:"

# Namespace prefix in a Commons file page URL.
COMMONS_FILE_PREFIX = "File:"


def unlink(text: str) -> str:
    """Replace wiki links with their visible text: ``[[a|b]]`` -> ``b``."""
    text = _LINK_WITH_LABEL.sub(r"\2", text)
    return _PLAIN_LINK.sub(r"\1", text)


def clean_filename(title: str) -> str:
    """Strip the local file namespace prefix from a page title."""
    if title.startswith(FILE_NAMESPACE_PREFIX):
        return title[len(FILE_NAMESPACE_PREFIX) :]
    return title


def commons_filename_from_url(commons_url: str) -> str:
    """The file name a Commons file page URL points at.

    ``…/wiki/File:%27Alter%27_G%C3%A4nsberg.jpg`` becomes
    ``'Alter' Gänsberg.jpg``: percent-decoded, and with the underscores of the
    URL turned back into the spaces the title actually has.
    """
    _, prefix, name = commons_url.partition(COMMONS_FILE_PREFIX)
    if not prefix:
        return ""
    return unquote(name).replace("_", " ").strip()


def _template_end(text: str, start: int) -> int | None:
    """Index just past the ``}}`` closing the template that opens at `start`."""
    depth = 0
    index = start
    while index < len(text) - 1:
        pair = text[index : index + 2]
        if pair == "{{":
            depth += 1
            index += 2
        elif pair == "}}":
            depth -= 1
            index += 2
            if depth == 0:
                return index
        else:
            index += 1
    return None


def find_template(
    text: str, names: Sequence[str] = FORM_TEMPLATES
) -> tuple[int, int] | None:
    """Span of the first call to one of `names`, or ``None`` if there is none."""
    for match in _TEMPLATE_START.finditer(text):
        if match.group(1) not in names:
            continue
        end = _template_end(text, match.start())
        if end is not None:
            return match.start(), end
    return None


def _split_parameters(body: str) -> list[str]:
    """Split a template body on its top-level pipes.

    The first part is the template name; nested templates and links keep their
    own pipes, which is why this is not a plain ``str.split``.
    """
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    index = 0

    while index < len(body):
        pair = body[index : index + 2]
        if pair in ("{{", "[["):
            depth += 1
        elif pair in ("}}", "]]"):
            depth = max(0, depth - 1)
        elif body[index] == "|" and depth == 0:
            parts.append("".join(current))
            current = []
            index += 1
            continue
        else:
            current.append(body[index])
            index += 1
            continue

        current.append(pair)
        index += 2

    parts.append("".join(current))
    return parts


def _trailing_space(text: str) -> str:
    """The whitespace a template parameter ends with, so new ones can match it."""
    return text[len(text.rstrip()) :]


def set_template_parameters(
    text: str, values: Mapping[str, str], names: Sequence[str] = FORM_TEMPLATES
) -> str | None:
    """Set named parameters in a page's form template.

    Existing parameters are overwritten in place, missing ones appended in the
    layout the template already uses. Returns ``None`` when the page has no such
    template, and the text unchanged when every value is already there.
    """
    span = find_template(text, names)
    if span is None:
        return None

    start, end = span
    parts = _split_parameters(text[start + 2 : end - 2])

    for name, value in values.items():
        for index, part in enumerate(parts[1:], start=1):
            key, separator, old = part.partition("=")
            if separator and key.strip() == name:
                parts[index] = f"{key}={value}{_trailing_space(old)}"
                break
        else:
            parts.append(f"{name}={value}{_trailing_space(parts[-1])}")

    return f"{text[:start]}{{{{{'|'.join(parts)}}}}}{text[end:]}"


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
