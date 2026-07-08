#!/usr/bin/env python3
"""Parse LPDP 2026 university list PDFs into raw row dicts."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    import pdfplumber
except ImportError:
    print("pdfplumber required", file=sys.stderr)
    sys.exit(1)

from parse_utils import (
    clean_cell,
    detect_beasiswa_from_page,
    is_data_row_no,
    pick_largest_table,
    skip_header_rows,
)

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "data" / "raw" / "pdfs"

STEM = "STEM Bidang STEM"
PENDUKUNG = "STEM Bidang Pendukung STEM"
SHARE = "SHARE"


def _raw_row(
    *,
    source: str,
    page: int,
    kategori: str,
    tipe: str,
    beasiswa: str,
    jenjang: str = "",
    bidang: str = "",
    perguruan_tinggi: str = "",
    program_studi: str = "",
    negara: str = "",
) -> dict[str, Any]:
    return {
        "_source": source,
        "_page": page,
        "Kategori": kategori,
        "Tipe": tipe,
        "Beasiswa": beasiswa,
        "Jenjang Studi": jenjang,
        "Bidang": bidang,
        "Perguruan Tinggi": perguruan_tinggi,
        "Program Studi": program_studi,
        "Negara": negara,
    }


def parse_ln(pdf_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    beasiswa = STEM

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            beasiswa = detect_beasiswa_from_page(text, beasiswa)

            for table in page.extract_tables() or []:
                if not table:
                    continue
                hdr = " ".join(clean_cell(c) for c in table[0]).lower()
                start = 1 if "no" in hdr else 0
                for r in table[start:]:
                    if not r or len(r) < 6:
                        continue
                    if not is_data_row_no(r[0]):
                        continue
                    rows.append(
                        _raw_row(
                            source="ln",
                            page=i,
                            kategori="luar negeri",
                            tipe="Luar Negeri",
                            beasiswa=beasiswa,
                            jenjang=clean_cell(r[1]),
                            bidang=clean_cell(r[2]),
                            perguruan_tinggi=clean_cell(r[3]),
                            program_studi=clean_cell(r[4]),
                            negara=clean_cell(r[5]),
                        )
                    )
    return rows


def parse_dn_style(
    pdf_path: Path,
    *,
    source: str,
    kategori: str,
    section_pages: list[tuple[int, int, str]] | None = None,
) -> list[dict[str, Any]]:
    """Parse DN/Afirmasi style 7-col sparse tables."""
    rows: list[dict[str, Any]] = []
    beasiswa = STEM

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if section_pages:
                for start, end, b in section_pages:
                    if start <= i <= end:
                        beasiswa = b
                        break
            else:
                beasiswa = detect_beasiswa_from_page(text, beasiswa)

            table = pick_largest_table(page.extract_tables())
            if not table:
                continue

            for r in skip_header_rows(table):
                if len(r) < 7:
                    continue
                no_val = clean_cell(r[0]) or clean_cell(r[1])
                if not is_data_row_no(no_val):
                    continue
                rows.append(
                    _raw_row(
                        source=source,
                        page=i,
                        kategori=kategori,
                        tipe="Dalam Negeri",
                        beasiswa=beasiswa,
                        jenjang=clean_cell(r[3]),
                        bidang=clean_cell(r[4]),
                        perguruan_tinggi=clean_cell(r[5]),
                        program_studi=clean_cell(r[6]),
                    )
                )
    return rows


def parse_dn(pdf_path: Path) -> list[dict[str, Any]]:
    return parse_dn_style(
        pdf_path,
        source="dn",
        kategori="dalam negeri",
        section_pages=[
            (2, 14, STEM),
            (15, 19, PENDUKUNG),
            (20, 26, SHARE),
        ],
    )


def parse_afirmasi(pdf_path: Path) -> list[dict[str, Any]]:
    return parse_dn_style(
        pdf_path,
        source="afirmasi",
        kategori="afirmasi",
        section_pages=[
            (2, 21, STEM),
            (22, 35, PENDUKUNG),
            (36, 60, SHARE),
        ],
    )


def _parse_unggulan_stem_row(row: list[Any], page: int) -> dict[str, Any] | None:
    cells = [clean_cell(c) for c in row if clean_cell(c)]
    if not cells or not is_data_row_no(cells[0]):
        return None
    # Typical collapsed: No, PT, Negara, Program Studi, Jenjang, Bidang
    if len(cells) >= 6:
        return _raw_row(
            source="unggulan",
            page=page,
            kategori="unggulan",
            tipe="Luar Negeri",
            beasiswa=STEM,
            perguruan_tinggi=cells[1],
            negara=cells[2] if len(cells) > 2 else "",
            program_studi=cells[3] if len(cells) > 3 else "",
            jenjang=cells[4] if len(cells) > 4 else "Magister",
            bidang=cells[5] if len(cells) > 5 else "",
        )
    return None


def parse_unggulan(pdf_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_all_subject = True

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if i < 4:
                continue
            text = page.extract_text() or ""
            if "Bidang Studi STEM" in text or re.search(r"\bB\.\s", text):
                in_all_subject = False

            for table in page.extract_tables() or []:
                if not table:
                    continue
                hdr = " ".join(clean_cell(c) for c in table[0]).lower()
                ncol = max(len(r) for r in table)

                # 4-col All Subject layout
                if ncol <= 6 and "program studi" in hdr and "negara" in hdr:
                    for r in table[1:]:
                        if not r or len(r) < 4:
                            continue
                        if not is_data_row_no(r[0]):
                            continue
                        ps = clean_cell(r[2])
                        rows.append(
                            _raw_row(
                                source="unggulan",
                                page=i,
                                kategori="unggulan",
                                tipe="Luar Negeri",
                                beasiswa="",
                                perguruan_tinggi=clean_cell(r[1]),
                                program_studi=ps,
                                negara=clean_cell(r[3]),
                            )
                        )
                    continue

                # Sparse STEM tables (many columns)
                if ncol >= 10 or "jenjang" in hdr:
                    for r in table[1:]:
                        parsed = _parse_unggulan_stem_row(r, i)
                        if parsed:
                            rows.append(parsed)
                    continue

                # Fallback 4-col without perfect header
                if ncol <= 6 and not in_all_subject:
                    for r in table[1:]:
                        if not r or len(r) < 4:
                            continue
                        if not is_data_row_no(r[0]):
                            continue
                        rows.append(
                            _raw_row(
                                source="unggulan",
                                page=i,
                                kategori="unggulan",
                                tipe="Luar Negeri",
                                beasiswa=STEM,
                                perguruan_tinggi=clean_cell(r[1]),
                                program_studi=clean_cell(r[2]),
                                negara=clean_cell(r[3]),
                                jenjang="Magister",
                            )
                        )
    return rows


def parse_all() -> dict[str, list[dict[str, Any]]]:
    return {
        "unggulan": parse_unggulan(PDF_DIR / "unggulan.pdf"),
        "luar_negeri": parse_ln(PDF_DIR / "ln.pdf"),
        "dalam_negeri": parse_dn(PDF_DIR / "dn.pdf"),
        "afirmasi": parse_afirmasi(PDF_DIR / "afirmasi.pdf"),
    }


def main() -> int:
    results = parse_all()
    for name, rows in results.items():
        print(f"{name}: {len(rows)} raw rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
