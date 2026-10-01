#!/usr/bin/env python3
"""Append/refresh the reviewer contract keys on sites/samsung/tasks.jsonl.

The first five keys of every row stay BYTE-IDENTICAL (asserted); the
``verifier_path`` and ``judge_rubric`` keys are (re)written to point at the
reviewer's deterministic verifiers (verify/verify_<n>.py, ground truth
hardcoded, graded offline) and pure-rule English judge rubrics. No ``answer``
key is ever written.

Run:  python3 append_rubrics.py <tasks.jsonl>
"""
import json
import re
import sys
from pathlib import Path

RUBRICS = {
    0: ("FACT CHECKPOINTS: Open the Smartphones catalog, apply the Galaxy Z "
        "series filter, clear it, sort by price low to high, open the cheapest "
        "phone's product page, open the Galaxy Z Fold8 Ultra product page, "
        "sign in as alice.j@test.com, add the cheapest phone to the wishlist "
        "and open the account or wishlist page. The answer MUST state how "
        "many phones the catalog lists, how many remain under the Galaxy Z "
        "filter, the cheapest phone's name and price, its rating and review "
        "count, the Galaxy Z Fold8 Ultra's price, and Alice's final wishlist "
        "item count. An empty answer, an answer without the on-site "
        "navigation, or a wishlist state that does not match the reported "
        "count is a FAIL."),
    1: ("FACT CHECKPOINTS: Open the Mobile Accessories catalog, search within "
        "it for case, keep only the Cases & Covers type, sort by customer "
        "rating, open the highest-rated product, sign in as bob.c@test.com, "
        "add that product to the wishlist and open the account or wishlist "
        "page. The answer MUST state how many results the case search "
        "returns, how many products remain under Cases & Covers, the "
        "highest-rated product's name and price, and Bob's final wishlist "
        "count. An empty answer, an answer without the on-site navigation, "
        "or a wishlist state that does not match the reported count is a "
        "FAIL."),
    2: ("FACT CHECKPOINTS: Open the TVs catalog, apply the 75\" - 84\" "
        "screen-size filter, add the Micro RGB TVs type filter, open the "
        "first remaining TV, clear the filters, sort by price high to low, "
        "sign in as carol.d@test.com, add the most expensive TV to the "
        "wishlist and open the account or wishlist page. The answer MUST "
        "state how many TVs the catalog lists, how many remain under each "
        "filter combination, the first remaining TV's name and price, the "
        "most expensive TV's name and price, and Carol's final wishlist "
        "count. An empty answer, an answer without the on-site navigation, "
        "or a wishlist state that does not match the reported count is a "
        "FAIL."),
    3: ("FACT CHECKPOINTS: Open the Refrigerators catalog, search within it "
        "for Family Hub, open the first match, open the Laundry catalog and "
        "sort it by price low to high, sign in as dana.k@test.com, add the "
        "Family Hub refrigerator to the wishlist and open the account or "
        "wishlist page. The answer MUST state how many refrigerators the "
        "Family Hub search matches, the first match's name, price and model "
        "code, the cheapest laundry product's name and price, and Dana's "
        "final wishlist count. An empty answer, an answer without the "
        "on-site navigation, or a wishlist state that does not match the "
        "reported count is a FAIL."),
    4: ("FACT CHECKPOINTS: Open the Galaxy S26 Ultra, Galaxy S26 and Galaxy "
        "S26 FE product pages, sign in as alice.j@test.com, add the Galaxy "
        "S26 Ultra to the wishlist, remove the Galaxy Tab S11 from it and "
        "open the account or wishlist page. The answer MUST state the S26 "
        "Ultra's model code, price and rating, its specification table's "
        "main display dimension, main display resolution, peak brightness "
        "and battery capacity (the unlabeled Battery-group value row is "
        "rendered under its group heading), the Galaxy S26's price and "
        "whether it shows a specification table, the S26 FE's price, and "
        "the final wishlist count. A battery-capacity value other than the "
        "one the page renders is a FAIL; an empty answer, an answer "
        "without the on-site navigation, or a wishlist state that does not "
        "match the reported count is a FAIL."),
    5: ("FACT CHECKPOINTS: Open the Galaxy S26 Ultra buy page, select the "
        "1TB storage option, change the color to Cobalt Violet, select the "
        "Unlocked carrier, sign in as alice.j@test.com, set the quantity to "
        "two, add the phone to the cart and open the cart page. The answer "
        "MUST state the default model code and price, the 1TB option's new "
        "price and model code, the resolved model code with Cobalt Violet, "
        "and the cart subtotal. An empty answer, an answer without the "
        "on-site navigation, or a cart state that does not match the "
        "reported subtotal is a FAIL."),
    6: ("FACT CHECKPOINTS: From the Smartphones catalog open the Galaxy Z "
        "Fold8 Ultra buy page, switch to the 1TB storage option, change the "
        "color to Violet Shadow, sign in as bob.c@test.com, add one unit "
        "to the cart, change the quantity to three, remove the item, "
        "reopen the Galaxy Z Fold8 Ultra product page, add it to the "
        "wishlist and open the account or wishlist page. The answer MUST "
        "state the default model code and price, the 1TB option's new "
        "price and model code, the resolved model code with Violet Shadow, "
        "the line total for one unit, the new line total at quantity "
        "three, that the cart is empty after removal, and Bob's final "
        "wishlist count. An empty answer, an answer without the on-site "
        "navigation, a leftover cart row in the database, or a wishlist "
        "state that does not match the reported count is a FAIL."),
    7: ("FACT CHECKPOINTS: Sign in as alice.j@test.com, open the Galaxy Tab "
        "S11 buy page from the Tablets catalog, add the default model to "
        "the cart, complete the delivery form with a valid US test "
        "address, select Samsung Pay, place the order and open the account "
        "or order-history page. The answer MUST state the default model "
        "code and price, the order number issued, the order total and "
        "tax, and how many orders Alice's history shows afterwards. An "
        "empty answer, an answer without the on-site navigation, or an "
        "order row that does not match the reported numbers is a FAIL."),
    8: ("FACT CHECKPOINTS: Open Galaxy Compare, select Galaxy S26 Ultra and "
        "Galaxy S26, run the comparison, add Galaxy Z Flip8 and run the "
        "three-way comparison, sign in as dana.k@test.com, add the Galaxy "
        "S26 Ultra to the wishlist from its product page, open its buy "
        "page and the account or wishlist page. The answer MUST state "
        "each model's main display dimension, weight, wide camera "
        "resolution and battery value from the rendered two-column "
        "comparison, which model has the larger battery, the Galaxy Z "
        "Flip8's main display dimension from the three-way comparison, "
        "the S26 Ultra buy page's default model code, and Dana's final "
        "wishlist count. Per-model values that the rendered columns do "
        "not carry are a FAIL; an empty answer, an answer without the "
        "on-site navigation, or a wishlist state that does not match the "
        "reported count is a FAIL."),
    9: ("FACT CHECKPOINTS: In Galaxy Compare select Galaxy Z Fold8 Ultra "
        "and Galaxy Z Fold8, clear and compare Galaxy S26 Ultra with "
        "Galaxy S25 Ultra instead, sign in as dana.k@test.com, add the "
        "Galaxy Z Fold8 Ultra to the wishlist from its product page and "
        "open the account or wishlist page. The answer MUST state both "
        "models' unfolded dimensions and weights from the rendered "
        "two-column comparison and which one is heavier, and the second "
        "comparison's per-model main display dimensions and peak "
        "brightness values, plus Dana's final wishlist count. Per-model "
        "values that the rendered columns do not carry are a FAIL; an "
        "empty answer, an answer without the on-site navigation, or a "
        "wishlist state that does not match the reported count is a "
        "FAIL."),
    10: ("FACT CHECKPOINTS: Open the Warranty Center from the Support page, "
         "check coverage for Phones, Tablets & Wearables with the Galaxy "
         "S26 Ultra 512GB model, check coverage for Home Appliances with a "
         "Bespoke refrigerator, sign in as carol.d@test.com, file a ticket "
         "under Phones, Tablets & Wearables with topic Warranty about the "
         "S26 Ultra screen and confirm the ticket confirmation page. The "
         "answer MUST state how many product categories the coverage "
         "checker lists, the S26 Ultra's coverage status and warranty "
         "period, the Bespoke refrigerator's coverage status, and the "
         "issued ticket number and its status. An empty answer, an answer "
         "without the on-site navigation, or a ticket row that does not "
         "match the reported number is a FAIL."),
    11: ("FACT CHECKPOINTS: From the Support home open the Warranty Center, "
         "open the FAQ about validating your warranty, check coverage for "
         "TV, Display & Home Theater with a TV model and for Phones, "
         "Tablets & Wearables with the Galaxy Watch9, open the Galaxy S26 "
         "Ultra buy page with the 512GB storage option, and open the "
         "Galaxy Watch9 product page and its buy page. The answer MUST "
         "state how many FAQ questions are listed, the validating-your-"
         "warranty FAQ's answer, the TV's coverage status and warranty "
         "period, the Watch9's coverage status, the resolved S26 Ultra "
         "512GB model code and price, and the Watch9's price and its buy "
         "page's default model code. An empty answer, an answer without "
         "the on-site navigation, or any database change is a FAIL."),
    12: ("FACT CHECKPOINTS: Sign in as alice.j@test.com, open the order "
         "history and both orders, open the wishlist, remove the Galaxy "
         "Tab S11, add the Galaxy Watch9 from the Watches catalog, open "
         "its buy page, and open the account page. The answer MUST state "
         "how many orders Alice has and their order numbers, the most "
         "recent order's item, quantity and delivery city, the older "
         "order's item and total, the Watch9 buy page's default model "
         "code, the final wishlist count and how many support tickets "
         "are listed. An empty answer, an answer without the on-site "
         "navigation, or a wishlist state that does not match the "
         "reported count is a FAIL."),
    13: ("FACT CHECKPOINTS: Sign in as dana.k@test.com, open the Warranty "
         "Center from the Support home, check coverage for Phones, "
         "Tablets & Wearables with the Galaxy Z Flip8, open Contact Us, "
         "file a ticket under Phones, Tablets & Wearables with topic "
         "Repair about the Z Flip8 hinge, and confirm the ticket on the "
         "account page. The answer MUST state the Z Flip8's coverage "
         "status and warranty period, the issued ticket number and its "
         "status, and that the ticket appears on the account page. An "
         "empty answer, an answer without the on-site navigation, or a "
         "ticket row that does not match the reported number is a FAIL."),
    14: ("FACT CHECKPOINTS: Use the header search to find Family Hub, open "
         "the first Bespoke Family Hub refrigerator result, search for "
         "Buds, search for case, sign in as bob.c@test.com, add the "
         "Galaxy Buds4 Pro to the wishlist and open the account or "
         "wishlist page. The answer MUST state how many results the "
         "Family Hub search returns (and their categories as shown), "
         "the first Bespoke Family Hub refrigerator's price and model "
         "code, the name and price of the first Buds search result as "
         "the header search actually lists it, how many results the "
         "case search returns, and Bob's final wishlist count. An empty "
         "answer, an answer without the on-site navigation, or a "
         "wishlist state that does not match the reported count is a "
         "FAIL."),
    15: ("FACT CHECKPOINTS: Create a new Samsung account (Frank Nova, "
         "frank.n@test.com) from the sign-up page, report what the "
         "account page shows, sign out and sign back in, open the "
         "Galaxy Watch9 product page from the Watches catalog, add it to "
         "the wishlist, open the Galaxy Z Flip8 product page and the "
         "account page. The answer MUST state what the account page "
         "shows for the new account (profile, order count, saved-items "
         "count and the support-tickets card), the profile name after "
         "signing back in, the Galaxy Z Flip8's price, and the final "
         "wishlist count. An empty answer, an answer without the on-site "
         "navigation, or an account/wishlist state that does not match "
         "the reported values is a FAIL."),
    16: ("FACT CHECKPOINTS: Open Shop All, the Tablets, Watches and Audio "
         "catalogs, the Audio catalog's first product, the TVs catalog, "
         "sign in as bob.c@test.com, open the order history and its "
         "order, and open the Galaxy Watch9 buy page from the Watches "
         "catalog. The answer MUST state how many products Shop All "
         "lists, how many products each of Tablets, Watches and Audio "
         "lists, the first Audio product's name and price, how many TVs "
         "are listed, Bob's order number and the item it contains, and "
         "the Watch9 buy page's default model code. An empty answer, an "
         "answer without the on-site navigation, or any database change "
         "is a FAIL."),
    17: ("FACT CHECKPOINTS: From the Watches catalog open the Galaxy Watch9 "
         "buy page, switch to the 44mm size and the LTE connectivity "
         "option, change the color to Graphite, sign in as "
         "carol.d@test.com, add the watch to the cart with quantity two, "
         "open the cart page and the checkout page. The answer MUST "
         "state the default model code and price, the resolved model "
         "code and price with 44mm and LTE, the resolved model code "
         "with Graphite, the cart subtotal, the options shown for the "
         "cart item, and the estimated tax shown on the checkout page. "
         "An empty answer, an answer without the on-site navigation, or "
         "a cart state that does not match the reported subtotal is a "
         "FAIL."),
    18: ("FACT CHECKPOINTS: Open the Galaxy Z Flip8 buy page from the "
         "Smartphones catalog, select the 512GB storage option, sign in "
         "as bob.c@test.com, add one unit to the cart, change the "
         "quantity to two, remove the item, reopen the buy page from "
         "the Smartphones catalog keeping the default storage, add one "
         "unit to the cart again and open the cart page. The answer "
         "MUST state the default model code and price, the 512GB "
         "option's new price and model code, the cart subtotal and item "
         "count at quantity two, and the new cart subtotal and the "
         "options shown for the re-added item. An empty answer, an "
         "answer without the on-site navigation, or a cart state that "
         "does not match the reported subtotals is a FAIL."),
    19: ("FACT CHECKPOINTS: From the Smartphones catalog open the Galaxy "
         "S25 Ultra product page, use Galaxy Compare to compare it with "
         "the Galaxy S26 Ultra, sign in as alice.j@test.com, add the "
         "Galaxy S25 Ultra to the wishlist, open the Galaxy Z Flip8 "
         "product page and the account or wishlist page. The answer "
         "MUST state the S25 Ultra's model code, price and rating, its "
         "specification table's main display dimension and peak "
         "brightness, both models' weights from the rendered "
         "two-column comparison and which model is heavier, the Galaxy "
         "Z Flip8's price, and Alice's final wishlist count. Weights "
         "the rendered columns do not carry are a FAIL; an empty "
         "answer, an answer without the on-site navigation, or a "
         "wishlist state that does not match the reported count is a "
         "FAIL."),
}


def main():
    path = Path(sys.argv[1])
    lines = path.read_text().splitlines()
    out_lines = []
    for n, line in enumerate(lines):
        if not line.strip():
            continue
        row = json.loads(line)
        idx = int(row["id"].split("--")[1])
        prefix = line[:line.index('"verifier_path"')]
        new_row = {
            "web_name": row["web_name"],
            "id": row["id"],
            "ques": row["ques"],
            "web": row["web"],
            "upstream_url": row["upstream_url"],
            "verifier_path": f"sites/samsung/verify/verify_{idx}.py",
            "judge_rubric": RUBRICS[idx],
        }
        # byte-identity assertion on the original five keys
        for key in ("web_name", "id", "ques", "web", "upstream_url"):
            old = json.dumps(row[key], ensure_ascii=False)
            new = json.dumps(new_row[key], ensure_ascii=False)
            assert old == new, f"row {n}: key {key} changed"
        assert "answer" not in new_row
        new_line = json.dumps(new_row, ensure_ascii=False)
        # byte-identity assertion: the new line must begin with the exact
        # original bytes covering the first five keys
        assert new_line.startswith(prefix), (
            f"row {n}: first-five-key prefix bytes changed")
        out_lines.append(new_line)
    path.write_text("\n".join(out_lines) + "\n")
    print(f"rewrote {len(out_lines)} rows with reviewer verifier_path + "
          f"judge_rubric (first five keys byte-identical, no answer key)")


if __name__ == "__main__":
    main()
