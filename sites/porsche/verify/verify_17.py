import re

from verify_lib import (added_rows, check_only_tables_changed, check_seed_contract,
                        check_trajectory_identity, contains_amount, contains_phrase,
                        contains_ref, entered_identity, final_answer, navigated_cart,
                        navigated_checkout, navigated_order_page, navigated_shop_product,
                        navigated_sign_in, rows_of, run_verifier, user_by_email)

TASK_ID = "Porsche--17"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    judge.check("visited_product_page",
                navigated_shop_product(traj, "classic-leather-jacket-P-P1140-590"),
                "required: Classic Leather Jacket product page")
    judge.check("visited_cart", navigated_cart(traj),
                "required: /shop/cart with the item added")
    judge.check("visited_checkout", navigated_checkout(traj),
                "required: /shop/checkout")
    judge.check("visited_order_page", navigated_order_page(traj),
                "required: order confirmation page")
    # sign-in with the demo account (checkout links the order to the user)
    judge.check("entered_demo_email", entered_identity(traj, "casey.taylor@test.com"),
                "required: checkout/sign-in with casey.taylor@test.com")
    # DB delta: one shop_orders row + its shop_order_items row, nothing else
    casey = user_by_email(initial_db, "casey.taylor@test.com")
    judge.check("demo_user_present", casey is not None, "casey.taylor@test.com in seed")
    check_only_tables_changed(judge, initial_db, after_db, {"shop_orders", "shop_order_items"})
    orders = added_rows(after_db, initial_db, "shop_orders", "id")
    judge.check("exactly_one_order", len(orders) == 1, f"shop_orders delta = {len(orders)}")
    order = orders[0] if orders else {}
    judge.check("order_confirmed", order.get("status") == "confirmed")
    judge.check("order_email", (order.get("email") or "").lower() == "casey.taylor@test.com",
                f"order email {order.get('email')!r}")
    judge.check("order_user", order.get("user_id") == (casey or {}).get("id"),
                f"order linked to casey.taylor (user_id={order.get('user_id')})")
    judge.check("recipient_name", order.get("first_name") == "Casey" and order.get("last_name") == "Taylor")
    judge.check("order_address",
                (order.get("street") or "") == "4500 9th Ave NE"
                and (order.get("city") or "") == "Seattle"
                and (order.get("state") or "") == "WA"
                and (order.get("zip") or "") == "98105",
                f"shipping address {order.get('street')!r}, {order.get('city')!r}, "
                f"{order.get('state')!r} {order.get('zip')!r}")
    judge.check("order_amounts",
                order.get("subtotal_cents") == 533000 and order.get("shipping_cents") == 0
                and order.get("total_cents") == 533000,
                f"subtotal={order.get('subtotal_cents')} shipping={order.get('shipping_cents')} "
                f"total={order.get('total_cents')}")
    items = added_rows(after_db, initial_db, "shop_order_items", "id")
    expected = {"Classic Leather Jacket": (2, 199000), "Trench Coat": (1, 135000)}
    products = {p["id"]: p["name"] for p in rows_of(initial_db, "shop_products")}
    observed = {products.get(it["product_id"]): (it["quantity"], it["unit_price_cents"]) for it in items}
    judge.check("exact_order_items", len(items) == 2 and observed == expected and all(it["order_id"] == order.get("id") for it in items))
    judge.check("both_unit_prices", contains_amount(answer, 1990) and contains_amount(answer, 1350))
    judge.check("both_products", contains_phrase(answer, "Classic Leather Jacket") and contains_phrase(answer, "Trench Coat"))
    # answer gates: order number matched against the DB row, amounts hardcoded
    m = re.search(r"\b(PS[A-Z0-9]{6,14})\b", answer)
    judge.check("answer_order_number",
                bool(m) and m.group(1) == order.get("order_number"),
                f"answer order number {m.group(1) if m else None} vs DB "
                f"{order.get('order_number')!r}")
    judge.check("answer_order_total", contains_amount(answer, 5330),
                "order total $245.00")
    judge.check("answer_shipping_charge",
                contains_phrase(answer, "free") or contains_amount(answer, 0),
                "shipping charge $0.00 (free)")
    judge.check("answer_unit_price", contains_amount(answer, 5330),
                "unit price $245.00")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
