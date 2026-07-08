# LPDP CTRL+F

**Control your Future** - Cari universitas impianmu untuk beasiswa LPDP.

From awardee to calon awardee. Pro-bono dan tidak menerima mentorship berbayar.

## Features

- **Pencarian Universitas** - Cari dari 29.000+ program studi LPDP (2026)
- **Filter STEM / SHARE / Pendukung** - Filter berdasarkan jenis beasiswa
- **Filter Afirmasi** - Filter khusus jalur afirmasi
- **Resume Analyzer** - Analisis CV dengan AI untuk rekomendasi universitas
- **Download Panduan** - Unduh panduan & daftar universitas resmi LPDP

## Tech Stack

- **Frontend**: Vanilla HTML/CSS/JS
- **Backend**: Python Flask (DigitalOcean App Platform)
- **AI**: OpenAI GPT-4
- **Data**: PDF ETL pipeline (`pdfplumber`) → JSON

## Quick Start

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env dengan OPENAI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start servers
./start.sh
```

Website: http://localhost:8000  
API: http://localhost:8080/api  
Live: https://lpdpfind.allrize.tech

## University data (ETL)

Data universitas di-parse dari PDF resmi LPDP 2026:

| PDF | Kategori | Lokasi level |
|-----|----------|--------------|
| Daftar Universitas Unggulan | `unggulan` | Negara |
| Daftar Universitas LN | `luar negeri` | Negara |
| Daftar Universitas DN (Umum) | `dalam negeri` | Provinsi |
| Daftar Universitas Afirmasi | `afirmasi` | Provinsi |

**Refresh data:**

```bash
pip install -r data/requirements-etl.txt
cd data/scripts
python3 download_lpdp_pdfs.py   # fetch PDFs → data/raw/pdfs/
python3 build_lookups.py        # rebuild lookup tables
python3 build_universities.py   # parse + normalize → data/processed/
python3 validate.py             # structural checks + diff report

# Deploy to frontend
cp ../processed/universities.json ../../frontend/universities.json
```

Output schema (11 fields): `No`, `Kategori`, `Beasiswa`, `Jenjang Studi`, `Bidang`, `Perguruan Tinggi`, `Program Studi`, `Lokasi`, `Region`, `Tipe`.

Garbled PDF extractions are dropped and logged to `data/processed/garble_dropped.json`.

See [data/README.md](data/README.md) for pipeline details.

## Deployment

Pushes to `main` auto-deploy via DigitalOcean App Platform (`lpdpfind`).

```bash
git push origin main
doctl apps list-deployments ba88d1b1-ed58-43fe-8ab6-ed4bcee13307
```

## Author

**Rizaldy Utomo**  
LPDP Awardee, Carnegie Mellon University  
rutomo@andrew.cmu.edu

---

*Copyright dokumen dari website resmi LPDP. Situs ini bertujuan untuk mempermudah pencarian universitas saja.*
