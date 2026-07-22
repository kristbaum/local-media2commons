"""Normalisation of the free-form ``Lizenz`` values coming out of the local wiki.

The SMW property holds anything from a clean ``cc-by-sa-3.0`` to a whole wiki
table pasted into the field, so every consumer (the step 3 report and the
step 4 transform) needs the same cleanup. Canonical names produced here are the
keys used by :func:`is_commons_compatible` and :func:`license_template`.
"""

from __future__ import annotations

import re

NO_LICENSE = "No license specified"
UNRECOGNIZED = "Unrecognized license"
MALFORMED = "Malformed license data"

# Canonical name -> Commons license template.
COMMONS_TEMPLATES = {
    "CC-BY-SA-3.0": "{{self|CC-BY-SA-3.0}}",
    "CC-BY-SA-4.0": "{{self|CC-BY-SA-4.0}}",
    "CC-BY-3.0": "{{self|CC-BY-3.0}}",
    "CC-BY-4.0": "{{self|CC-BY-4.0}}",
    "Public Domain": "{{PD-self}}",
    "GFDL": "{{self|GFDL}}",
}

# Only these may be uploaded to Commons.
COMMONS_COMPATIBLE = frozenset(COMMONS_TEMPLATES)

# Lowercased raw value -> canonical name. Values not listed here are kept as-is
# so that unexpected licenses stay visible in the report instead of being
# silently bucketed.
LICENSE_MAPPINGS = {
    "cc-by-sa-3.0": "CC-BY-SA-3.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-sa-3": "CC-BY-SA-3.0",
    "cc-by-3.0": "CC-BY-3.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-nc-3.0": "CC-BY-NC-3.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc-by-nc-sa-3.0": "CC-BY-NC-SA-3.0",
    "cc-by-nc-sa-4.0": "CC-BY-NC-SA-4.0",
    "cc-by-nc-nd-3.0": "CC-BY-NC-ND-3.0",
    "cc-by-nc-nd-4.0": "CC-BY-NC-ND-4.0",
    "cc-by-nd-4.0": "CC-BY-ND-4.0",
    "copyright": "Copyright",
    "public domain": "Public Domain",
    "pd": "Public Domain",
    "pdm": "Public Domain",
    "pd-alt": "Public Domain",
    "gemeinfrei": "Public Domain",
    "gfdl": "GFDL",
    "bildlizenz-stadtarchiv": "Stadtarchiv License",
    "bildlizenz-yadvashem": "Yad Vashem License",
    "bildlizenz-jmf": "JMF License",
    "noc-nc-1.0": "NOC-NC-1.0",
    "out of copyright - non commercial re-use": "Out of copyright (non-commercial)",
    "non-commercial use only": "Non-commercial only",
    "non-commercial usw only": "Non-commercial only",
}

# Matches a Creative Commons identifier embedded in a longer string.
_CC_PATTERN = re.compile(r"(cc-by(?:-sa|-nc|-nd)*-?\d*\.?\d*)")

# Last-resort patterns applied to values that are still markup soup.
_SALVAGE_PATTERNS = ["cc-by-sa-3.0", "cc-by-sa-4.0", "cc-by-nc", "copyright"]


def strip_markup(value: str) -> str:
    """Remove HTML tags, wiki links and wiki tables, then collapse whitespace."""
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\[\[[^\]]+\]\]", "", value)
    value = re.sub(r"\{\|.*?\|\}", "", value, flags=re.DOTALL)
    return re.sub(r"\s+", " ", value).strip()


def normalize_license(raw_value: str | None) -> str:
    """Turn a raw ``Lizenz`` value into a canonical license name.

    Always returns a name; unusable input becomes one of :data:`NO_LICENSE`,
    :data:`UNRECOGNIZED` or :data:`MALFORMED`.
    """
    if not raw_value or not raw_value.strip():
        return NO_LICENSE

    value = strip_markup(raw_value.strip())

    cc_match = _CC_PATTERN.search(value.lower())
    if cc_match:
        value = cc_match.group(1)

    normalized = LICENSE_MAPPINGS.get(value.lower(), value)

    # Still markup soup: try to salvage a known license from the noise.
    if len(normalized) > 50 or "{" in normalized or "cellspacing" in normalized:
        for pattern in _SALVAGE_PATTERNS:
            if pattern in normalized.lower():
                return LICENSE_MAPPINGS.get(pattern, UNRECOGNIZED)
        return MALFORMED

    return normalized


def is_commons_compatible(license_name: str | None) -> bool:
    """Whether files under this license may be uploaded to Wikimedia Commons."""
    return license_name in COMMONS_COMPATIBLE


def license_template(license_name: str) -> str | None:
    """Commons wikitext template for a canonical license name, if one exists."""
    return COMMONS_TEMPLATES.get(license_name)
