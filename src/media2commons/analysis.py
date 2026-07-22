"""Aggregate statistics over the step 4 metadata dump."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from .dates import extract_year
from .licenses import is_commons_compatible, normalize_license

# Metadata columns whose non-empty count is reported as "completeness".
COMPLETENESS_FIELDS = {
    "description": "Beschreibung",
    "author": "Urheber",
    "source": "Quellangaben",
}


@dataclass
class MediaStats:
    """Counts derived from a full pass over the step 4 rows."""

    total_images: int = 0
    exists_on_commons: int = 0
    licenses: Counter[str] = field(default_factory=Counter)
    years: Counter[int] = field(default_factory=Counter)
    decades: Counter[int] = field(default_factory=Counter)
    completeness: Counter[str] = field(default_factory=Counter)

    @property
    def not_on_commons(self) -> int:
        return self.total_images - self.exists_on_commons

    @property
    def commons_compatible(self) -> int:
        """Files whose license would allow an upload, regardless of duplicates."""
        return sum(
            count
            for name, count in self.licenses.items()
            if is_commons_compatible(name)
        )

    @property
    def images_with_year(self) -> int:
        return sum(self.years.values())

    def percent(self, count: int) -> float:
        """`count` as a percentage of all images (0.0 when there are none)."""
        if not self.total_images:
            return 0.0
        return count / self.total_images * 100


def row_is_on_commons(row: dict[str, str]) -> bool:
    return row.get("exists_on_commons", "").strip().lower() == "true"


def analyze_rows(rows: Iterable[dict[str, str]]) -> MediaStats:
    """Collect :class:`MediaStats` from step 4 result rows."""
    stats = MediaStats()

    for row in rows:
        stats.total_images += 1

        if row_is_on_commons(row):
            stats.exists_on_commons += 1

        stats.licenses[normalize_license(row.get("Lizenz"))] += 1

        year = extract_year(row.get("Erstellungsdatum"))
        if year:
            stats.years[year] += 1
            stats.decades[year // 10 * 10] += 1

        for label, column in COMPLETENESS_FIELDS.items():
            if row.get(column, "").strip():
                stats.completeness[label] += 1

    return stats
