"""Step 3 (report): summarise licenses, dates and metadata completeness.

Reads: ``data/step3_result.csv``. Writes: ``data/step3_report.txt`` and prints
the long-form report to stdout.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..analysis import analyze_rows
from ..config import STEP3_REPORT, STEP3_RESULT
from ..csv_io import iter_rows
from ..reporting import render_report, render_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP3_RESULT)
    parser.add_argument("--output", type=Path, default=STEP3_REPORT)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}. Run step 3 first.")

    stats = analyze_rows(iter_rows(args.input))
    print(render_report(stats))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_summary(stats), encoding="utf-8")
    print(f"Summary saved to: {args.output}")


if __name__ == "__main__":
    main()
