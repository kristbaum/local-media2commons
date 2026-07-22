"""Text rendering of :class:`~media2commons.analysis.MediaStats`."""

from __future__ import annotations

from datetime import datetime

from .analysis import MediaStats
from .licenses import NO_LICENSE, is_commons_compatible

TOP_LICENSES = 15
TOP_YEARS = 10
TOP_DECADES = 10


def _mark(license_name: str) -> str:
    return "✓" if is_commons_compatible(license_name) else "✗"


def _count_line(stats: MediaStats, label: str, count: int) -> str:
    return f"{label}: {count:,} ({stats.percent(count):.1f}%)"


def render_report(stats: MediaStats, now: datetime | None = None) -> str:
    """The full human-readable analysis, meant for stdout."""
    now = now or datetime.now()
    out: list[str] = []

    out.append("=" * 70)
    out.append("FÜRTHWIKI MEDIA ANALYSIS REPORT")
    out.append("=" * 70)
    out.append(f"Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    out.append("")

    out.append("📊 BASIC STATISTICS")
    out.append("-" * 40)
    out.append(f"Total images analyzed: {stats.total_images:,}")
    out.append(_count_line(stats, "Already exist on Commons", stats.exists_on_commons))
    out.append(_count_line(stats, "Not on Commons", stats.not_on_commons))
    out.append("")

    out.append(f"📋 LICENSE DISTRIBUTION (Top {TOP_LICENSES})")
    out.append("-" * 40)
    for name, count in stats.licenses.most_common(TOP_LICENSES):
        out.append(f"{_mark(name)} {_count_line(stats, name, count)}")
    remaining = len(stats.licenses) - TOP_LICENSES
    if remaining > 0:
        remaining_count = sum(
            count for _, count in stats.licenses.most_common()[TOP_LICENSES:]
        )
        out.append(f"   ... and {remaining} other licenses: {remaining_count:,}")
    out.append("")

    out.append("📝 METADATA COMPLETENESS")
    out.append("-" * 40)
    for label in ("description", "author", "source"):
        count = stats.completeness[label]
        out.append(_count_line(stats, f"Images with {label}", count))
    out.append("")

    out.append(f"📅 CREATION YEAR DISTRIBUTION (Top {TOP_YEARS})")
    out.append("-" * 40)
    out.append(_count_line(stats, "Images with year data", stats.images_with_year))
    out.append("")
    for year, count in stats.years.most_common(TOP_YEARS):
        out.append(_count_line(stats, str(year), count))
    out.append("")

    out.append("📅 CREATION BY DECADE")
    out.append("-" * 40)
    for decade in sorted(stats.decades, reverse=True)[:TOP_DECADES]:
        out.append(_count_line(stats, f"{decade}s", stats.decades[decade]))
    out.append("")

    out.append("🚀 COMMONS UPLOAD POTENTIAL")
    out.append("-" * 40)
    compatible = stats.commons_compatible
    out.append(_count_line(stats, "Images with Commons-compatible licenses", compatible))
    out.append(_count_line(stats, "Images not yet on Commons", stats.not_on_commons))
    out.append(
        f"Potential Commons uploads: ~{min(compatible, stats.not_on_commons):,} images"
    )
    out.append("(Estimated based on license compatibility)")
    out.append("")

    out.extend(render_insights(stats))
    return "\n".join(out)


def render_insights(stats: MediaStats) -> list[str]:
    """Short prose takeaways appended to the end of the report."""
    out = ["💡 KEY INSIGHTS & RECOMMENDATIONS", "-" * 40]

    cc_by_sa = stats.licenses["CC-BY-SA-3.0"] + stats.licenses["CC-BY-SA-4.0"]
    out.append(
        f"• {cc_by_sa:,} images ({stats.percent(cc_by_sa):.1f}%) are CC-BY-SA "
        "licensed - excellent for Commons!"
    )

    copyrighted = stats.licenses["Copyright"]
    if copyrighted:
        out.append(
            f"• {copyrighted:,} images ({stats.percent(copyrighted):.1f}%) have "
            "copyright restrictions"
        )

    unlicensed = stats.licenses[NO_LICENSE]
    if unlicensed:
        out.append(f"• {unlicensed:,} images lack license information")

    description_pct = stats.percent(stats.completeness["description"])
    if description_pct > 95:
        out.append("• Excellent description coverage!")
    elif description_pct < 80:
        out.append("• Consider improving description completeness")

    if stats.percent(stats.completeness["author"]) > 80:
        out.append("• Good author attribution coverage")
    else:
        out.append("• Author information could be improved")

    recent = sum(count for year, count in stats.years.items() if year >= 2020)
    if recent:
        out.append(f"• {recent:,} images from 2020+ show active documentation")

    out.append("• Focus on CC-BY-SA content for immediate Commons uploads")
    out.append("• Review copyright status for proprietary content")
    return out


def render_summary(stats: MediaStats, now: datetime | None = None) -> str:
    """The condensed summary that gets written to disk."""
    now = now or datetime.now()
    out = [
        "FürthWiki Media Analysis Summary",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Total images: {stats.total_images:,}",
        f"On Commons: {stats.exists_on_commons:,}",
        f"Not on Commons: {stats.not_on_commons:,}",
        "",
        "Top 10 License distribution:",
    ]

    for name, count in stats.licenses.most_common(10):
        out.append(f"  {_mark(name)} {name}: {count:,} ({stats.percent(count):.1f}%)")

    out.append("")
    out.append("Metadata completeness:")
    for label, title in (
        ("description", "Description"),
        ("author", "Author"),
        ("source", "Source"),
    ):
        count = stats.completeness[label]
        out.append(f"  {title}: {count:,} ({stats.percent(count):.1f}%)")

    return "\n".join(out) + "\n"
