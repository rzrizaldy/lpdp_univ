# LPDP University Data Pipeline

Reproducible ETL from official LPDP 2026 PDFs to `universities.json`.

## Source PDFs

Stored in `data/raw/pdfs/`:

| File | Official list |
|------|---------------|
| `unggulan.pdf` | Daftar Universitas Unggulan |
| `ln.pdf` | Daftar Universitas LN |
| `dn.pdf` | Daftar Universitas DN (Umum) |
| `afirmasi.pdf` | Daftar Universitas Afirmasi |

Download URLs are in `data/scripts/download_lpdp_pdfs.py`.

## Scripts

| Script | Description |
|--------|-------------|
| `download_lpdp_pdfs.py` | Download PDFs from LPDP |
| `build_lookups.py` | Generate `data/lookups/*.json` |
| `parse_lpdp_pdfs.py` | PDF → raw rows (per source) |
| `normalize.py` | Country/province mapping, bidang simplification, garble removal |
| `build_universities.py` | Merge all sources, assign `No`, write JSON |
| `validate.py` | Schema checks, Lokasi granularity, diff vs baseline |

## Lookups

| File | Purpose |
|------|---------|
| `country_region.json` | PDF `Negara` → `Lokasi` (country) + `Region` (continent) |
| `pt_province.json` | `Perguruan Tinggi` → `Lokasi` (province) + `Region` (island) |
| `bidang_aliases.json` | Simplify composite bidang strings |
| `garble_aliases.json` | Fix known PDF OCR corruption |

## Output

| File | Description |
|------|-------------|
| `processed/universities.json` | Final merged dataset (copy to `frontend/`) |
| `processed/{unggulan,luar_negeri,dalam_negeri,afirmasi}.json` | Per-source normalized rows |
| `processed/validation_report.json` | Stats, diff vs previous data, errors |
| `processed/garble_dropped.json` | Rows removed due to garbled extraction |

## Rules

- **No cross-category dedup** — same program can appear in `unggulan` + `luar negeri`
- **Lokasi**: country for LN/Unggulan, province for DN/Afirmasi
- **Garble**: corrupted rows are deleted, not shipped
- **Row count drift** vs old data is expected when LPDP updates PDFs

## Current stats (Jul 2026 refresh)

- **29,662** total rows
- 25,663 luar negeri · 1,264 unggulan · 815 dalam negeri · 1,920 afirmasi
- 246 garbled rows dropped
