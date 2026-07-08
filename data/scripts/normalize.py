#!/usr/bin/env python3
"""Normalize parsed PDF rows: lookups, bidang, garble removal."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOOKUPS = ROOT / "data" / "lookups"
PROCESSED = ROOT / "data" / "processed"

GARBLE_DIGIT_RE = re.compile(r"[a-zA-Z]\d+[a-zA-Z]|\d{3,}")
STEM = "STEM Bidang STEM"
VALID_BEASISWA = {"", STEM, "SHARE", "STEM Bidang Pendukung STEM"}

SCHEMA_KEYS = [
    "No",
    "Kategori",
    "Beasiswa",
    "Jenjang Studi",
    "Bidang",
    "Perguruan Tinggi",
    "Program Studi",
    "Lokasi",
    "Region",
    "Tipe",
]


def _load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def simplify_bidang(raw: str, aliases: dict[str, str]) -> str:
    s = raw.strip()
    if not s:
        return ""
    if s in aliases:
        return aliases[s]
    if ":" in s:
        s = s.split(":", 1)[0].strip()
    if s in aliases:
        return aliases[s]
    return s


def resolve_country(negara: str, country_map: dict) -> tuple[str, str]:
    if not negara:
        return "", ""
    if negara in country_map:
        e = country_map[negara]
        return e["lokasi"], e["region"]
    low = negara.lower()
    for k, e in country_map.items():
        if k.lower() == low:
            return e["lokasi"], e["region"]
    # Title-case fallback
    tc = negara.title()
    if tc in country_map:
        e = country_map[tc]
        return e["lokasi"], e["region"]
    return negara, ""


def apply_garble_aliases(value: str, aliases: dict[str, str]) -> str:
    if value in aliases:
        return aliases[value]
    for bad, good in aliases.items():
        if bad in value:
            value = value.replace(bad, good)
    return value


def is_garbled(value: str, *, field: str, tipe: str, country_map: dict) -> str | None:
    """Return garble reason or None if OK."""
    if not value:
        return None
    v = value.strip()
    if GARBLE_DIGIT_RE.search(v):
        return f"digit_pattern_in_{field}"
    if field == "Lokasi" and tipe == "Luar Negeri":
        if v not in country_map:
            if not any(k.lower() == v.lower() for k in country_map):
                return "unknown_country_lokasi"
    # Only flag extreme lengths on Lokasi (country names should be short)
    if field == "Lokasi" and len(v) > 60:
        return f"too_long_{field}"
    return None


def normalize_row(
    raw: dict[str, Any],
    *,
    country_map: dict,
    pt_map: dict,
    bidang_aliases: dict,
    garble_aliases: dict,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (normalized_row, dropped_info)."""
    tipe = raw["Tipe"]
    kategori = raw["Kategori"]

    pt = apply_garble_aliases(raw.get("Perguruan Tinggi", "").strip(), garble_aliases)
    ps = apply_garble_aliases(raw.get("Program Studi", "").strip(), garble_aliases)
    bidang = simplify_bidang(raw.get("Bidang", ""), bidang_aliases)
    beasiswa = raw.get("Beasiswa", "") or ""
    jenjang = raw.get("Jenjang Studi", "") or ""

    if tipe == "Luar Negeri":
        negara = apply_garble_aliases(raw.get("Negara", "").strip(), garble_aliases)
        lokasi, region = resolve_country(negara, country_map)
    else:
        pt_entry = pt_map.get(pt, {})
        lokasi = pt_entry.get("lokasi", "")
        region = pt_entry.get("region", "")

    row = {
        "Kategori": kategori,
        "Beasiswa": beasiswa,
        "Jenjang Studi": jenjang,
        "Bidang": bidang,
        "Perguruan Tinggi": pt,
        "Program Studi": ps,
        "Lokasi": lokasi,
        "Region": region,
        "Tipe": tipe,
    }

    if not pt or not ps:
        return None, {
            **raw,
            "reason": "missing_pt_or_prodi",
            "normalized": row,
        }

    for field in ("Lokasi", "Perguruan Tinggi", "Program Studi"):
        val = row[field]
        val = apply_garble_aliases(val, garble_aliases)
        row[field] = val
        reason = is_garbled(val, field=field, tipe=tipe, country_map=country_map)
        if reason:
            return None, {**raw, "reason": reason, "normalized": row}

    return row, None


def normalize_rows(raw_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    country_map = _load_json(LOOKUPS / "country_region.json")
    pt_map = _load_json(LOOKUPS / "pt_province.json")
    bidang_aliases = _load_json(LOOKUPS / "bidang_aliases.json")
    garble_aliases = _load_json(LOOKUPS / "garble_aliases.json")

    ok: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []

    for raw in raw_rows:
        row, drop = normalize_row(
            raw,
            country_map=country_map,
            pt_map=pt_map,
            bidang_aliases=bidang_aliases,
            garble_aliases=garble_aliases,
        )
        if row:
            ok.append(row)
        elif drop:
            dropped.append(drop)
    return ok, dropped


def assign_numbers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, row in enumerate(rows, start=1):
        out.append({"No": i, **row})
    return out
