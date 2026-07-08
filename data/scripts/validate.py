#!/usr/bin/env python3
"""Validate universities.json structure and emit diff report."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
LOOKUPS = ROOT / "data" / "lookups"
OLD_JSON = ROOT / "frontend" / "universities.json"

SCHEMA_KEYS = [
    "No", "Kategori", "Beasiswa", "Jenjang Studi", "Bidang",
    "Perguruan Tinggi", "Program Studi", "Lokasi", "Region", "Tipe",
]
VALID_BEASISWA = {"", "STEM Bidang STEM", "SHARE", "STEM Bidang Pendukung STEM"}
CONTINENTS = {
    "Amerika", "Eropa", "Asia", "Oseania", "Afrika", "Australia",
}
ISLANDS = {
    "Jawa", "Sumatera", "Kalimantan", "Sulawesi", "Bali", "Nusa Tenggara",
    "Maluku", "Papua", "Bangka Belitung", "DKI Jakarta",
}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize import is_garbled  # noqa: E402


def row_key(r: dict) -> tuple:
    return (
        r.get("Kategori", ""),
        r.get("Perguruan Tinggi", ""),
        r.get("Program Studi", ""),
        r.get("Lokasi", ""),
        r.get("Beasiswa", ""),
    )


def validate(data: list[dict], country_map: dict) -> tuple[list[str], dict]:
    errors: list[str] = []
    stats: dict = {
        "total": len(data),
        "kategori": dict(Counter(r.get("Kategori", "") for r in data)),
        "beasiswa": dict(Counter(r.get("Beasiswa", "") for r in data)),
        "tipe": dict(Counter(r.get("Tipe", "") for r in data)),
    }

    seen_nos: set[int] = set()
    for i, row in enumerate(data):
        for key in SCHEMA_KEYS:
            if key not in row:
                errors.append(f"row {i}: missing key {key}")

        no = row.get("No")
        if no in seen_nos:
            errors.append(f"duplicate No: {no}")
        seen_nos.add(no)

        if not row.get("Perguruan Tinggi") or not row.get("Program Studi"):
            errors.append(f"row {no}: empty PT or Prodi")

        beasiswa = row.get("Beasiswa", "")
        if beasiswa not in VALID_BEASISWA:
            errors.append(f"row {no}: invalid Beasiswa '{beasiswa}'")

        tipe = row.get("Tipe", "")
        lokasi = row.get("Lokasi", "")
        region = row.get("Region", "")

        if tipe == "Luar Negeri":
            for field in ("Lokasi", "Perguruan Tinggi", "Program Studi"):
                reason = is_garbled(row.get(field, ""), field=field, tipe=tipe, country_map=country_map)
                if reason:
                    errors.append(f"row {no}: garble {field} ({reason})")
        elif tipe == "Dalam Negeri":
            for field in ("Perguruan Tinggi", "Program Studi"):
                reason = is_garbled(row.get(field, ""), field=field, tipe=tipe, country_map=country_map)
                if reason:
                    errors.append(f"row {no}: garble {field} ({reason})")

    if stats["total"] == 0:
        errors.append("empty dataset")

    return errors, stats


def diff_report(old: list[dict], new: list[dict]) -> dict:
    old_keys = {row_key(r) for r in old}
    new_keys = {row_key(r) for r in new}
    return {
        "old_total": len(old),
        "new_total": len(new),
        "delta": len(new) - len(old),
        "old_kategori": dict(Counter(r.get("Kategori", "") for r in old)),
        "new_kategori": dict(Counter(r.get("Kategori", "") for r in new)),
        "added_count": len(new_keys - old_keys),
        "removed_count": len(old_keys - new_keys),
        "added_sample": [list(k) for k in list(new_keys - old_keys)[:10]],
        "removed_sample": [list(k) for k in list(old_keys - new_keys)[:10]],
    }


def main() -> int:
    data_path = PROCESSED / "universities.json"
    if not data_path.exists():
        print("Run build_universities.py first", file=sys.stderr)
        return 1

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    country_map = json.loads((LOOKUPS / "country_region.json").read_text(encoding="utf-8"))
    errors, stats = validate(data, country_map)

    dropped_path = PROCESSED / "garble_dropped.json"
    dropped_count = 0
    if dropped_path.exists():
        dropped = json.loads(dropped_path.read_text(encoding="utf-8"))
        dropped_count = len(dropped)

    report: dict = {
        "passed": len(errors) == 0,
        "errors": errors[:50],
        "error_count": len(errors),
        "stats": stats,
        "garble_dropped_count": dropped_count,
    }

    if OLD_JSON.exists():
        with open(OLD_JSON, encoding="utf-8") as f:
            old = json.load(f)
        report["diff_vs_baseline"] = diff_report(old, data)

    out = PROCESSED / "validation_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Total rows: {stats['total']}")
    print(f"Kategori: {stats['kategori']}")
    print(f"Beasiswa: {stats['beasiswa']}")
    print(f"Garble dropped: {dropped_count}")
    if report.get("diff_vs_baseline"):
        d = report["diff_vs_baseline"]
        print(f"Delta vs baseline: {d['delta']:+d} ({d['old_total']} -> {d['new_total']})")

    if errors:
        print(f"\nFAILED: {len(errors)} errors")
        for e in errors[:10]:
            print(f"  - {e}")
        return 1

    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
