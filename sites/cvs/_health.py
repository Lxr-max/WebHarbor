"""Read-only health contract for the CVS mirror."""
import os
import sqlite3
from pathlib import Path


def health():
    database = Path(os.environ.get("CVS_INSTANCE_PATH", str(Path(__file__).parent / "instance"))) / "cvs.db"
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            products = connection.execute("SELECT count(*) FROM product").fetchone()[0]
            stores = connection.execute("SELECT count(*) FROM store").fetchone()[0]
            ready = connection.execute("SELECT count(*) FROM snapshot_meta").fetchone()[0] == 1
        return {"ok": ready and products > 0 and stores > 0, "site": "cvs", "products": products, "stores": stores}
    except sqlite3.Error:
        return {"ok": False, "site": "cvs"}
