#!/usr/bin/env python3
"""Per-site health probe (called by control_server)."""
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))


def health():
    db = os.path.join(BASE, "instance", "backcountry.db")
    counts = {}
    if os.path.exists(db):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            for table in ("products", "product_skus", "reviews", "categories",
                          "brands", "users", "orders"):
                counts[table] = con.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            con.close()
    return {"ok": counts.get("products", 0) > 0, "site": "backcountry",
            "rows": counts}
