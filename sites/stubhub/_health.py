"""Per-site health probe (called by control_server after /reset)."""
import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "instance", "stubhub.db")
SEED = os.path.join(BASE_DIR, "instance_seed", "stubhub.db")


def health():
    result = {"ok": True, "site": "stubhub"}
    try:
        conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        try:
            for table in ("events", "listings", "performers", "venues",
                          "users", "orders", "sales", "payment_cards",
                          "favorites", "gift_card_orders", "category_nodes"):
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                result[table] = count
            # benchmark users present
            n = conn.execute(
                "SELECT COUNT(*) FROM users WHERE email LIKE '%@test.com'").fetchone()[0]
            result["benchmark_users"] = n
            # every event with a listing must expose a price window
            bad = conn.execute(
                "SELECT COUNT(*) FROM events WHERE listing_count > 0 "
                "AND (min_price IS NULL OR max_price IS NULL)").fetchone()[0]
            result["events_missing_price_window"] = bad
            if bad:
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
