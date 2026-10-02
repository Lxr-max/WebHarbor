"""Inspect the mirror database without writing state."""
import sqlite3
from pathlib import Path


def health():
    path = Path(__file__).resolve().parent / "instance" / "us_doj.db"
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        count = connection.execute("SELECT COUNT(*) FROM page").fetchone()[0]
    return {"ok": count > 0, "site": "us_doj", "pages": count}
