#!/usr/bin/env python3
"""Build final universities.json from parsed PDFs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
SCRIPTS = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS))

from normalize import assign_numbers, normalize_rows  # noqa: E402
from parse_lpdp_pdfs import parse_all  # noqa: E402


def main() -> int:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    parsed = parse_all()
    all_normalized: list[dict] = []
    all_dropped: list[dict] = []

    for name, raw_rows in parsed.items():
        rows, dropped = normalize_rows(raw_rows)
        all_normalized.extend(rows)
        all_dropped.extend(dropped)

        out_path = PROCESSED / f"{name}.json"
        numbered = assign_numbers(rows)
        out_path.write_text(json.dumps(numbered, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: {len(raw_rows)} raw -> {len(rows)} normalized ({len(dropped)} dropped)")

    final = assign_numbers(all_normalized)
    (PROCESSED / "universities.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (PROCESSED / "garble_dropped.json").write_text(
        json.dumps(all_dropped, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nTotal: {len(final)} rows, {len(all_dropped)} dropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
