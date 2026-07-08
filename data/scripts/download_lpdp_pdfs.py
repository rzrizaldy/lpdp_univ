#!/usr/bin/env python3
"""Download official LPDP 2026 university list PDFs."""

from __future__ import annotations

import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "raw" / "pdfs"
SCRATCHPAD = ROOT / "scratchpad" / "pdfs"

PDFS = {
    "unggulan.pdf": "https://lpdp-belakang.kemenkeu.go.id/storage/programs/files/gFsullYNXUdvWMhYEFxPW6fP1AAXbO2xQo2raD8K.pdf",
    "ln.pdf": "https://lpdp-belakang.kemenkeu.go.id/storage/programs/files/jlJ2KIq5jiagKnrDYMAKA96BSy6BUSYsKquNUGkN.pdf",
    "dn.pdf": "https://lpdp-belakang.kemenkeu.go.id/storage/programs/files/cp1CS1h8RYdxqNJY5RW2FqYbvDykbfNneOXpoY12.pdf",
    "afirmasi.pdf": "https://lpdp-belakang.kemenkeu.go.id/storage/programs/files/Tfy4rZGuKXBP5mmIHOvwQCmtWAMxZ1Ky7t8vfX5w.pdf",
}


def download(url: str, dest: Path) -> None:
    print(f"Downloading {dest.name} ...")
    urllib.request.urlretrieve(url, dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  -> {dest} ({size_mb:.1f} MB)")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, url in PDFS.items():
        dest = OUT_DIR / name
        scratch = SCRATCHPAD / name
        if scratch.exists() and not dest.exists():
            shutil.copy2(scratch, dest)
            print(f"Copied {scratch} -> {dest}")
        elif not dest.exists():
            download(url, dest)
        else:
            print(f"Already exists: {dest}")

    print("\nPDF inventory:")
    for name in PDFS:
        path = OUT_DIR / name
        if path.exists():
            print(f"  {name}: {path.stat().st_size / 1024:.0f} KB")
        else:
            print(f"  {name}: MISSING")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
