"""Per-site health probe (called by control_server after /reset)."""
import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "instance", "trip_com.db")
SEED = os.path.join(BASE_DIR, "instance_seed", "trip_com.db")

MIN_COUNTS = {
    "users": 4,
    "cities": 11,
    "hotels": 1000,
    "room_rates": 500,
    "hotel_reviews": 60,
    "flight_routes": 6,
    "flights": 700,
    "attractions": 130,
    "attraction_packages": 95,
    "coupons": 4,
    "guides": 6,
    "hotel_bookings": 4,
    "flight_bookings": 2,
    "attraction_bookings": 2,
    "wishlist_items": 12,
}


def health():
    result = {"ok": True, "site": "trip_com"}
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
