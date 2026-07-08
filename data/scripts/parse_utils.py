#!/usr/bin/env python3
"""Shared parsing utilities for LPDP PDF tables."""

from __future__ import annotations

import re
from typing import Any

NO_RE = re.compile(r"^\d+\.?$")


def clean_cell(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val).replace("\n", " ")).strip()


def is_data_row_no(val: Any) -> bool:
    s = clean_cell(val)
    return bool(s) and s.replace(".", "").isdigit()


def collapse_sparse_row(row: list[Any], expected_cols: int | None = None) -> list[str]:
    """Extract non-empty cells from a sparse pdfplumber row."""
    cells = [clean_cell(c) for c in row if clean_cell(c)]
    return cells


def pick_largest_table(tables: list[list[list[Any]]] | None) -> list[list[Any]] | None:
    if not tables:
        return None
    return max(tables, key=lambda t: len(t))


def skip_header_rows(table: list[list[Any]]) -> list[list[Any]]:
    """Skip header rows; return data rows only."""
    data = []
    for row in table:
        joined = " ".join(clean_cell(c) for c in row).lower()
        if not joined:
            continue
        if "no" in joined and ("perguruan" in joined or "program" in joined or "jenjang" in joined):
            continue
        if joined in {"jenjang studi", "jenjang", "studi"}:
            continue
        data.append(row)
    return data


def detect_beasiswa_from_page(text: str, default: str) -> str:
    t = text.upper()
    if "BEASISWA SHARE" in t:
        return "SHARE"
    if "PENDUKUNG STEM" in t:
        return "STEM Bidang Pendukung STEM"
    if "BIDANG STEM" in t and "PENDUKUNG" not in t:
        return "STEM Bidang STEM"
    return default
