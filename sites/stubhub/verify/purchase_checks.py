"""Purchase outcomes validated by ticket identity and exact saved-state deltas."""
from verify_lib import table_diff, check_only_tables_changed, check_answer_number

def purchase(judge, traj, initial_db, after_db, task_no):
    answer = traj.get("final_answer", "")
    new_user = task_no == 12
    ua, ur, uc = table_diff(initial_db, after_db, "users")
    judge.check("account_delta", len(ua) == int(new_user) and not ur and not uc)
    uid = next(iter(ua.values()))["id"] if ua else 2
    added, removed, changed = table_diff(initial_db, after_db, "orders")
    judge.check("order_delta", len(added) == 1 and not removed and not changed)
    if len(added) != 1:
        return
    order = next(iter(added.values()))
    upstream_id = 160436498 if new_user else 160436506
    event = initial_db.execute("SELECT * FROM events WHERE upstream_id=?", (upstream_id,)).fetchone()
    listing = initial_db.execute("SELECT * FROM listings WHERE id=?", (order["listing_id"],)).fetchone()
    judge.check("ticket_identity", listing is not None and listing["event_id"] == event["id"] and not listing["is_sold"])
    if listing is None:
        return
    qty = 1 if new_user else 2
    price = listing["price"]
    minimum = initial_db.execute("SELECT min(price) FROM listings WHERE event_id=? AND is_sold=0 AND quantity>=1", (event["id"],)).fetchone()[0]
    judge.check("eligible_ticket", listing["quantity"] >= qty and (price == minimum if new_user else price < 250))
    delivery = "instant" if new_user else "ups"
    delivery_fee = 0 if new_user else 14.95
    total = round(price * qty + delivery_fee + 2.95, 2)
    judge.check("order_fields", order["user_id"] == uid and order["event_id"] == event["id"]
                and order["quantity"] == qty and order["unit_price"] == price
                and order["delivery_method"] == delivery and order["delivery_fee"] == delivery_fee
                and order["processing_fee"] == 2.95 and abs(order["total"] - total) < .005
                and order["status"] == "Confirmed" and bool(order["card_last4"]))
    if not new_user:
        judge.check("visa_payment", order["card_last4"].lower().startswith("visa"))
        check_answer_number(judge, answer, "delivery_fee", delivery_fee)
        check_answer_number(judge, answer, "processing_fee", 2.95)
    judge.check("reference_matches", order["order_number"] in answer)
    check_answer_number(judge, answer, "paid_total", total)
    la, lr, lc = table_diff(initial_db, after_db, "listings")
    judge.check("inventory_delta", not la and not lr and set(lc) == {(listing["id"],)})
    for before, after in lc.values():
        remaining = before["quantity"] - qty
        judge.check("inventory_remaining", after["quantity"] == remaining and after["is_sold"] == int(remaining == 0)
                    and all(before[k] == after[k] for k in before if k not in {"quantity", "is_sold"}))
    ca, cr, cc = table_diff(initial_db, after_db, "payment_cards")
    judge.check("wallet_preserved", len(ca) == int(new_user) and not cr and not cc)
    for card in ca.values():
        judge.check("card_owner", card["user_id"] == uid and card["is_default"] == 1 and card["last4"] in order["card_last4"])
    na, nr, nc = table_diff(initial_db, after_db, "notifications")
    judge.check("notifications_preserved", len(na) == 1 and not nr and not nc and all(r["user_id"] == uid for r in na.values()))
    check_only_tables_changed(judge, initial_db, after_db, ("users", "orders", "listings", "payment_cards", "notifications"))
