"""Step 5: keep only uploadable files and render their Commons wikitext.

Reads: ``data/step4_result.csv``. Writes: ``data/step5_commons_ready.csv``.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from ..config import STEP4_RESULT, STEP5_RESULT
from ..csv_io import iter_rows, write_rows
from ..transform import COMMONS_READY_FIELDS, transform_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=STEP4_RESULT)
    parser.add_argument("--output", type=Path, default=STEP5_RESULT)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}. Run step 4 first.")

    rows = list(transform_rows(iter_rows(args.input)))
    write_rows(args.output, rows, COMMONS_READY_FIELDS)

    print("=" * 60)
    print("STEP 5: COMMONS TRANSFORMATION COMPLETE")
    print("=" * 60)
    print(f"Files ready for upload: {len(rows):,}")
    print(f"Output saved to: {args.output}")
    print()

    licenses = Counter(row["license"] for row in rows)
    print("License distribution in output:")
    for name, count in licenses.most_common():
        print(f"  {name}: {count:,}")

    if rows:
        print()
        print(f"Sample wikitext for {rows[0]['commons_filename']}:")
        print("-" * 40)
        print(rows[0]["wikitext"])


if __name__ == "__main__":
    main()
