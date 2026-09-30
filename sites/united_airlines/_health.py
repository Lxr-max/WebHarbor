"""Per-site health probe (called by control_server after /reset)."""
import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "instance", "united_airlines.db")
SEED = os.path.join(BASE_DIR, "instance_seed", "united_airlines.db")

MIN_COUNTS = {
    "users": 4,
    "airports": 40,
    "flights": 30,
    "fares": 100,
    "aircraft": 8,
    "bookings": 4,
    "booking_legs": 4,
    "passengers": 4,
    "help_articles": 20,
    "cabin_info": 6,
    "policy_articles": 4,
    "deals": 8,
}


def health():
    result = {"ok": True, "site": "united_airlines"}
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
