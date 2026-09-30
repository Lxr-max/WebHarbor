"""Per-site health probe (called by control_server after /reset)."""
import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "instance", "student_com.db")
SEED = os.path.join(BASE_DIR, "instance_seed", "student_com.db")

MIN_COUNTS = {
    "users": 4,
    "universities": 250,
    "cities": 15,
    "properties": 400,
    "property_universities": 400,
    "jobs": 100,
    "bookmarks": 8,
    "enquiries": 3,
}


def health():
    result = {"ok": True, "site": "student_com"}
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            for table, minimum in MIN_COUNTS.items():
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                result[table] = count
                if count < minimum:
                    result["ok"] = False
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["error"] = str(exc)[:200]
    return result


if __name__ == "__main__":
    print(json.dumps(health()))
    sys.exit(0 if health()["ok"] else 1)
