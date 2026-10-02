"""Per-site health probe for the Speedo mirror (end-to-end)."""
import sqlite3
from pathlib import Path


def health():
    db_path = Path(__file__).resolve().parent / "instance" / "speedo.db"
    conn = sqlite3.connect(db_path)
    try:
        counts = {}
        for table in ["users", "products", "product_sizes", "collections",
                      "collection_memberships", "departments", "athletes",
                      "articles", "content_pages", "faq_entries", "orders",
                      "order_items", "cart_items", "wishlist_items",
                      "addresses", "payment_cards", "discount_codes"]:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = row[0]
        ok = (counts["products"] >= 200 and counts["collections"] >= 40
              and counts["users"] >= 4 and counts["athletes"] >= 10
              and counts["articles"] >= 8 and counts["orders"] >= 4
              and counts["content_pages"] >= 15 and counts["faq_entries"] >= 8)
        return {"ok": bool(ok), "site": "speedo", "counts": counts}
    finally:
        conn.close()
