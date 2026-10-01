#!/usr/bin/env python3
"""test_verifiers.py — adversarial contract tests for the trader_joes verifier
suite (review branch orch/review/trader_joes, contributor base
orch/contribute/trader_joes @ bda7f0a7).

Guarantees (run with pytest):
  * each honest fixture (from the reviewer's two independent Playwright rounds
    on the review container tj-review-r2-container, seed md5
    34e1af0cc66a317223e889081c2381b4) PASSES its verify_<n>.py;
  * every adversarial negative FAILS (zero false positives):
      - no-op trajectories (20),
      - answer-only shortcuts with no navigation (20),
      - wrong-answer trajectories (20, fabricated per question point),
      - stale-DB trajectories (all 17 stateful tasks: the DB delta is undone
        while the answer claims success),
      - read-only violations (all 3 read-only tasks get an injected write),
      - tampered packages (wrong task_id / off-site URL / cross-port URL /
        not-terminated / empty answer / pre-mutated seed),
      - task-specific confusions (T0 remove wrong list row, T1 wrong signup
        email, T3 wrong My Store, T4 wrong subscriber, T5 subscribe-only
        without the unsubscribe flip, T7 wrong added sku, T8 wrong added sku,
        T10 wrong My Store, T11 wrong added sku, T12 wrong added sku,
        T13 wrong quantity change, T14 wrong final rows, T15 wrong added sku,
        T16 wrong My Store, T17 wrong cheddar quantity, T18 wrong MOC
        quantity, T19 wrong added sku).
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

VERIFY = Path(__file__).resolve().parent
EV = Path("/data/zhaoyang-user-projects/websyn/wh-tj-review-evidence")
FIXTURES = EV / "fixtures"
TMP = EV / "verify_runs" / "_pytest_tmp"
PY = sys.executable

TASK_IDS = [f"Trader Joe's--{n}" for n in range(20)]
# stateful: the honest walk leaves a DB delta (shopping list / user_stores /
# subscribers / signup)
# r2: T9 is stateful too (carol adds the description-linked product)
STATEFUL = [0, 1, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
# read-only: the honest walk leaves the DB row-identical (T2 add+remove and
# T6 add+increase+remove both restore the seed exactly)
READ_ONLY = [n for n in range(20) if n not in STATEFUL]


def run_verifier(n: int, run_dir: Path):
    proc = subprocess.run(
        [PY, str(VERIFY / f"verify_{n}.py"), "--run_dir", str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        verdict = json.loads(proc.stdout)
    except json.JSONDecodeError:
        verdict = {"pass": False, "reason": proc.stdout[-300:] or proc.stderr[-300:]}
    return verdict


def clone(n: int, tag: str) -> Path:
    dst = TMP / f"{n}_{tag}"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(FIXTURES / str(n), dst)
    return dst


def set_traj(run_dir: Path, **changes):
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    traj.update(changes)
    p.write_text(json.dumps(traj, indent=2))


def mutate_answer(run_dir: Path, new_answer: str):
    set_traj(run_dir, final_answer=new_answer)


def mutate_db(run_dir: Path, which: str, sql: str):
    db = sqlite3.connect(run_dir / which)
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        db.execute(stmt)
    db.commit()
    db.close()


def drop_nav(run_dir: Path):
    """Replace the whole trajectory with a homepage-only no-op walk."""
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    base = traj.get("start_url", "http://localhost:46137/")
    step = {"idx": 0, "action": "navigate", "thought": "look around",
            "params": {}, "url": base, "url_after": base,
            "extracted_content": ""}
    for s in traj.get("steps", []):
        for key in ("screenshot_before", "screenshot_after"):
            s.pop(key, None)
    traj["steps"] = [step]
    p.write_text(json.dumps(traj, indent=2))


# ---------------------------------------------------------------- honest PASS --

@pytest.mark.parametrize("n", range(20))
def test_honest_fixture_passes(n):
    verdict = run_verifier(n, FIXTURES / str(n))
    assert verdict["pass"], f"Trader Joe's--{n} honest fixture must PASS: {verdict['reason']}"


# ---------------------------------------------------------------- no-op FAIL --

@pytest.mark.parametrize("n", range(20))
def test_noop_fails(n):
    run_dir = clone(n, "noop")
    drop_nav(run_dir)
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} no-op must FAIL"


# ------------------------------------------------- answer-only shortcut FAIL --

SHORTCUT_ANSWER = {
    0: "17 products match the Gluten Free filter in Bakery. The cheapest is Glazed Chocolate "
       "Donut Holes at $3.49/6 Oz. Country of origin: Product of USA; calories per serving: "
       "240; first listed allergen: CONTAINS EGG. After adding it the list total is 9 and the "
       "Pumpkin Cream Cheese Spread quantity is 2. After removing the Pumpkin Bread & Muffin "
       "Mix the new total is 8. After logging out and back in the list persisted with total 8.",
    1: "The What's New listing shows 25 products. The list has 3 items: Pumpkin O's Cereal "
       "$3.49/12 Oz; Pumpkin Cream Cheese Spread $2.79/8 Oz; Ooey Gooey Cheese Blend "
       "$4.99/12 Oz. After increasing the cereal's quantity by one it shows 2 and the new "
       "total is 4. After logging out and back in the list persisted with total 4.",
    2: "The Bacon, Apple, and Brie Panini serves 1-2 and its time is 15 mins - 25 mins; its "
       "fourth listed ingredient is '8 slices of your favorite TJ's Apple'. The linked bread, "
       "Ciabatta Demi-Baguette, is $1.49 for 6.2 Oz. The Prosciutto Melon Bites serve 4-8. "
       "After adding the bread, Bob's list total is 7 with the mandarin orange chicken at "
       "quantity 2; after removing the bread the final total is 6.",
    3: "ZIP 98052 within 5 miles lists 3 stores; the closest is Redmond (140) (phone "
       "425-883-1624, Monday hours: 09:00 - 21:00). After setting it as My Store the header "
       "shows Redmond (140). The second-closest store's phone is 425-641-5069. Within 10 "
       "miles the count is 10, and Oregon lists 16 stores.",
    4: "Announcements category counts: Customer Updates 3, Store Openings 52, Special Trading "
       "Hours 0, Caring For Our Communities 1, Recalls 2. The newest store opening is "
       "'Herriman, UT—Opens Friday, October 9th!' (2026-09-28). The newest recall affects "
       "Fiesta Salad with Shrimp. Gift card 6510000000123456 has $25.00 and 6510000000445566 "
       "has $12.49. Subscribing shows: Welcome aboard!",
    5: "Gift card balances: 6510000000654321 $51.37, 6510000000112233 $0.00, "
       "6510000000987654 $100.00, 6510000000445566 $12.49. For cards without a peel or "
       "scratch-off PIN call 1-888-556-6619. Subscribing: Welcome aboard! Unsubscribing: "
       "You've been unsubscribed. felice.t@example.com has been removed from the Trader Joe's "
       "eNewsletter list - we're sorry to see you go. Dana's My Store is Charlotte - Piper "
       "Glen (742).",
    6: "From The Freezer sorted by Price High to Low: most expensive is Korean Style Beef "
       "Short Ribs at $14.99/20 Oz; second is Beef Bulgogi. With the Vegan filter 38 products "
       "match; the first vegan product is Jumeokbap ($4.99/10.58 Oz) and the second one's "
       "price is $4.99. After adding it Dana's list total is 1; after adding one more it is "
       "2; after removing it entirely the final count is 0. The What's New listing shows 25 "
       "products.",
    7: "Searching pumpkin returns 82 results: 56 products, 15 recipes, 11 in Everything Else. "
       "The first product result is $3.99 / 6 Oz, origin Product of United States. The first "
       "recipe result serves 8 with total time 45 minutes. The first Everything Else item is "
       "'Cozy Up to Congee' (2026-02-23). After adding the first product result Alice's list "
       "total is 9 and the pumpkin bisque quantity is 3.",
    8: "For the Pantry lists 235 products in total. With the Vegan filter 19 match; adding "
       "the Kosher filter leaves 11. The first product under both filters is Granola Butter "
       "at $5.49/12 Oz; its country of origin is Made in United States and its first listed "
       "ingredient is OATS. The second product's price is $3.49. After adding the first "
       "product Carol's list total is 5.",
    9: "The Desserts filter shows 92 recipes; adding the Let's Bake! fun tag leaves 18. The "
       "first recipe under both is 'Blueberry Corn Cake': serves 9, time 55 mins, first "
       "ingredient '1/2 cup TJ's Canola Oil'. With the fun tag cleared but Desserts kept, "
       "the first recipe is 'AB&J Banana Bark Boats' serving 4; the product linked in its "
       "description is Dark Chocolate Bark with Almond, Pretzel & Sea Salt at $5.99 / 10 Oz. "
       "Searching for that product's title returns 1 result; after adding it Carol's list "
       "total is 5.",
    10: "Massachusetts lists 27 stores. The Brookline store's address is 1317 Beacon St, "
        "phone 617-278-9997, Sunday hours 08:00 - 21:00. The first store listed for "
        "Massachusetts is Acton (511) (phone 978-266-8908). After setting the Brookline store "
        "as My Store the header shows Brookline (501). Connecticut lists 13 stores; the "
        "first one's phone is 203-739-0098.",
    11: "The One Seasoning Wonder guide was published 2026-09-16; it showcases Polenta & "
        "Veggie Stacks, Umami Parm Popcorn and Roasted Pork Tenderloin & Potatoes with Honey "
        "Umami Butter, and features TJ's Mushroom & Company Multipurpose Umami Seasoning "
        "Blend. The first showcased recipe serves 4 with total time 30 minutes. The What's "
        "New listing shows 25 products and the first one is Bare Bones Succulent Garden. "
        "After adding it Alice's list total is 9.",
    12: "The newest podcast episode is 'Episode 112: Time for Tacos at Trader Joe's' "
        "(published 21 Sep 2026); the second-newest is episode #2 'Episode 111: Can't Help "
        "Falling for this Trader Joe's Shopping List'. The More Episodes table lists 12 "
        "episodes. The home page's podcast section is titled 'Podcast'. Pumpkin Pie Spice "
        "Bark is $5.49 / 8 Oz. After adding it Alice's list total is 9 and the pumpkin "
        "bisque quantity is 3; after increasing the bisque the total is 10; after removing "
        "the spice the total is 9.",
    13: "Gluten Free Multigrain Bread: $4.99 / 15.2 Oz, category Sliced Bread, first "
        "ingredient WATER, STARCH AND FLOUR BLEND, badges Gluten Free and Kosher. Organic "
        "Brown Rice & Quinoa Fusilli Pasta: $3.49 / 16 Oz, category Pastas & Grains, first "
        "ingredient ORGANIC BROWN RICE, badges Gluten Free, Organic and Kosher. Gluten Free "
        "Norwegian Crispbread: $4.79 / 7.55 Oz. Carol's list: multigrain bread quantity 1, "
        "total 4; after increasing the bread 5; after removing the crispbread the final "
        "total is 3.",
    14: "Carol's list initially has total 4: fusilli x1, crispbread x2, multigrain bread "
        "x1. After removing the crispbread the new total is 2. After decreasing the fusilli "
        "pasta the running total is 1. After adding the Gluten Free White Sandwich Bread it "
        "is 2. After adding the Gluten Free Breaded Shrimp the final item count is 3: "
        "multigrain bread x1, white sandwich bread x1, breaded shrimp x1.",
    15: "Searching cheese returns 128 products and 37 in Everything Else. The Just Here for "
        "the Cheese guide was published 2024-01-29 and its first featured product is Cheddar "
        "Cheese with Caramelized Onions ($11.99, category Wedges, Wheels, Loaves, Logs). The "
        "newest story is 'A Cider to Crow About' (2026-09-25). After adding that product "
        "Bob's list total is 7 and the dark chocolate peanut butter cups quantity is 1.",
    16: "Washington lists 33 stores. The Bellingham store on James Street: 2410 James St, "
        "phone 360-734-5166, Saturday hours 08:00 - 21:00. After setting it as My Store the "
        "header shows Bellingham (151). ZIP 98225 within 5 miles returns 2 stores; the "
        "closest one's phone is 360-734-5166 and its Sunday hours are 08:00 - 21:00. "
        "Widening the same ZIP search to 10 miles returns 2 stores.",
    17: "Shredded Unexpected Cheddar Cheese: $4.99 / 8 Oz, Product of United States, first "
        "ingredient CHEDDAR CHEESE, contains CONTAINS MILK. American Heritage Cream Cheese "
        "with Chives & Onions carries the Kosher badge, $2.79 / 8 Oz; the shredded cheddar "
        "is more expensive. Bob's shredded cheddar quantity is 2; after increasing it and "
        "adding the cream cheese the final total is 8.",
    18: "The What's New listing shows 25 products. The first product is $8.99 / 1 Each, "
        "limited-time: yes. After adding it Bob's list total is 7 with the mandarin orange "
        "chicken at 2; after increasing the chicken the new total is 8. The second What's "
        "New product is $1.99; searching for its title returns 1 results.",
    19: "The Entertaining section lists 17 articles; the first is 'Fall Forward With Spiced "
        "Chai Apple Crisp' (category label Common). The Guides listing shows 56 guides and "
        "the newest is 'One Seasoning Wonder' (published 2026-09-16); the first product it "
        "features is TJ's Mushroom & Company Multipurpose Umami Seasoning Blend. The "
        "Stories listing shows 67 stories and the newest is 'A Cider to Crow About' "
        "(published 2026-09-25). After adding the featured product Alice's list total is 9; "
        "after increasing its quantity by one the final total is 10.",
}


@pytest.mark.parametrize("n", range(20))
def test_answer_only_shortcut_fails(n):
    """Correct answer, but the agent never navigated anywhere (memory recall)."""
    run_dir = clone(n, "shortcut")
    drop_nav(run_dir)
    mutate_answer(run_dir, SHORTCUT_ANSWER[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} answer-only shortcut must FAIL"


# ------------------------------------------------------------ wrong answers --

WRONG_ANSWERS = {
    0: "12 products match the Gluten Free filter in Bakery. The cheapest is Glazed Pumpkin "
       "Donut Holes at $2.99. Country of origin: Product of Canada; calories per serving: "
       "150; first allergen: CONTAINS TREE NUTS. The list total is 11, Pumpkin Cream Cheese "
       "Spread quantity 3, after removal 9, persisted 9.",
    1: "The What's New listing shows 28 products. The list has 3 items: cereal $2.99, cream "
       "cheese $1.99, cheese blend $3.99. After increasing the cereal it shows 3 and the new "
       "total is 5. The list persisted with total 5.",
    2: "The panini serves 2-4 and takes 30 minutes; its fourth ingredient is '1 cup TJ's "
       "Brie'. The bread is $2.49 for 8 Oz. The Prosciutto Melon Bites serve 6-12. Bob's "
       "total is 9 with the chicken at 3; after removing the bread the final total is 8.",
    3: "ZIP 98052 within 5 miles lists 5 stores; the closest is Bellevue (131) (phone "
       "425-451-7200, Monday 10:00 - 20:00). The header shows Bellevue (131). The "
       "second-closest store's phone is 425-822-0203. Within 10 miles the count is 15, and "
       "Oregon lists 20 stores.",
    4: "Announcements counts: Customer Updates 5, Store Openings 60, Special Trading Hours "
       "2, Caring 3, Recalls 4. The newest opening is 'Lafayette, LA—Now Open!' (2026-09-17). "
       "The recall affects Mandarin Orange Chicken. The gift cards have $30.00 and $15.99. "
       "Subscribing shows: Thank you for subscribing!",
    5: "Balances: $60.00, $5.00, $200.00, $20.00. The no-PIN phone is 1-800-555-1234. "
       "Subscribing shows: You're in! Unsubscribing shows: You have been removed. Dana's My "
       "Store is Tigard (742).",
    6: "The most expensive freezer product is Beef Bulgogi at $11.99; second is Korean "
       "Style Beef Short Ribs. The Vegan filter gives 25 products; the first is Korean "
       "Beefless Bulgogi and the second is $3.99. Dana's list total is 2 after adding, 3 "
       "after increasing, and 1 after removing. What's New shows 28 products.",
    7: "Searching pumpkin returns 75 results: 40 products, 10 recipes, 25 in Everything "
       "Else. The first product is $2.99 / 12 Oz from Product of Canada. The first recipe "
       "serves 4 with 20 minutes. The first Everything Else item is 'We Come Bearing Fall' "
       "(2026-09-03). Alice's list total is 11 and the bisque quantity is 5.",
    8: "For the Pantry lists 300 products. Vegan gives 25; Vegan+Kosher gives 7. The first "
       "product is Marshmallows at $2.99, origin Product of Malawi, first ingredient SUGAR. "
       "The second product's price is $5.49. Carol's new total is 7.",
    9: "Desserts shows 100 recipes; with Let's Bake! 25 remain. The first recipe is 'Apple "
       "Pie': serves 6, 40 minutes, first ingredient flour. With the tag cleared the first "
       "is 'Blueberry Corn Cake' serving 12. The search returns 5 results.",
    10: "Massachusetts lists 30 stores. Brookline is at 200 Harvard St, phone 617-555-1212, "
        "Sunday 9:00 - 18:00. The first MA store is Allston (525), phone 617-999-8888. The "
        "header shows Brookline. Connecticut lists 20 stores; the first phone is "
        "860-555-1212.",
    11: "The guide was published 2026-08-01; it showcases three salads and features "
        "Unexpected Cheddar Cheese. The first recipe serves 6 with 45 minutes. What's New "
        "shows 28 products, first is Garlic Parsley Potato Kit. Alice's new total is 11.",
    12: "The newest episode is 'Episode 111' (2026-09-08); the second is episode #1 "
        "'Episode 110'. The table lists 15 episodes. The home podcast section is 'The "
        "Podcast'. Pumpkin Pie Spice is $3.49 / 12 Oz. Alice's new total is 11 and the "
        "bisque quantity is 5.",
    13: "The bread is $5.99 / 16 Oz in category Bakery, first ingredient RICE FLOUR, no "
        "Kosher badge. The pasta is $2.99 / 12 Oz in category Pantry, first ingredient "
        "SEMOLINA, with a Kosher badge. The crispbread is $3.99 / 6 Oz. Carol's bread "
        "quantity is 2, total 6, after increase 7, final total 5.",
    14: "Carol's list starts with total 5: fusilli x2, crispbread x2, multigrain x1. After "
        "removing the crispbread 3. After decreasing 2. After the first add 3. Final count "
        "4 with multigrain x1, white bread x2, shrimp x1.",
    15: "Searching cheese returns 100 products and 20 in Everything Else. The guide was "
        "published 2025-06-15 and features Unexpected Cheddar Cheese ($4.99, category "
        "Cheese). The newest story is 'A Cider to Crow About' (2026-09-25). Bob's new total "
        "is 9 and the cups quantity is 2.",
    16: "Washington lists 40 stores. Bellingham is at 100 Grand Ave, phone 360-555-1212, "
        "Saturday 9:00 - 18:00. The header shows Bellingham - North (274). ZIP 98225 "
        "within 5 miles returns 5 stores; the closest phone is 360-999-9999 and Sunday "
        "hours are 10:00 - 20:00.",
    17: "The cheddar is $6.99 / 12 Oz from Product of Canada, first ingredient MILK, "
        "contains CONTAINS SOY. The cream cheese carries a Vegan badge, $3.99 / 12 Oz; the "
        "cream cheese is more expensive. Bob's cheddar quantity is 1; the final total is "
        "10.",
    18: "What's New shows 28 products. The first is $9.99 / 2 Each, not limited-time. Bob's "
        "total is 9 with the chicken at 3; after increasing 10. The second product is "
        "$2.99; the search returns 5 results.",
    19: "The Entertaining section lists 25 articles; the first is 'Thanksgiving Timeline' "
        "(category Classic). The Guides listing shows 60 guides; the newest is 'We Can "
        "Cornbread That!' (2026-08-03), featuring Cornbread Stuffing. Alice's My Store is "
        "Find a Store; her new total is 11.",
}


@pytest.mark.parametrize("n", range(20))
def test_wrong_answer_fails(n):
    run_dir = clone(n, "wrong")
    mutate_answer(run_dir, WRONG_ANSWERS[n])
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} wrong answer must FAIL"


# ------------------------------------------------------------------ stale DB --

@pytest.mark.parametrize("n", STATEFUL)
def test_stale_db_fails(n):
    """Stateful task: the DB delta is undone but the answer claims success."""
    run_dir = clone(n, "stale")
    shutil.copy(run_dir / "initial.db", run_dir / "after.db")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} stale DB must FAIL"


# -------------------------------------------------------- read-only violation --

@pytest.mark.parametrize("n", READ_ONLY)
def test_readonly_violation_fails(n):
    """Read-only task: an injected write in the after-state FAILs."""
    run_dir = clone(n, "dirty")
    mutate_db(run_dir, "after.db",
              "INSERT INTO subscribers (email, status, created_at) "
              "VALUES ('dirty@probe.example', 'subscribed', '2026-10-01')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} read-only violation must FAIL"


# ----------------------------------------------------------- tampered packages --

@pytest.mark.parametrize("n", range(20))
def test_wrong_task_id_fails(n):
    run_dir = clone(n, "wrongid")
    set_traj(run_dir, task_id="Trader Joe's--99")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} wrong task_id must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_offsite_url_fails(n):
    run_dir = clone(n, "offsite")
    set_traj(run_dir, start_url="https://www.traderjoes.com/")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} off-site start_url must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_cross_port_url_fails(n):
    run_dir = clone(n, "crossport")
    p = run_dir / "trajectory.json"
    traj = json.loads(p.read_text())
    for s in traj.get("steps", []):
        if s.get("url_after", "").startswith("http://localhost:46137"):
            s["url_after"] = s["url_after"].replace("46137", "48137")
    p.write_text(json.dumps(traj, indent=2))
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} cross-port URL must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_not_terminated_fails(n):
    run_dir = clone(n, "unterminated")
    set_traj(run_dir, terminated=False, termination_reason="max_steps")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} unterminated run must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_empty_answer_fails(n):
    run_dir = clone(n, "emptyans")
    mutate_answer(run_dir, "")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} empty answer must FAIL"


@pytest.mark.parametrize("n", range(20))
def test_premutated_seed_fails(n):
    run_dir = clone(n, "badseed")
    mutate_db(run_dir, "initial.db",
              "INSERT INTO users (email, name, password_hash, joined) "
              "VALUES ('x@y.example', 'X', 'h', '2026-10-01')")
    verdict = run_verifier(n, run_dir)
    assert not verdict["pass"], f"Trader Joe's--{n} pre-mutated seed must FAIL"


# ------------------------------------------------- task-specific confusions --

def test_t0_wrong_row_removed_fails():
    """Agent removes the Organic Pumpkin row instead of the Pumpkin Bread & Muffin Mix."""
    run_dir = clone(0, "wrongremove")
    mutate_db(run_dir, "after.db",
              "DELETE FROM shopping_items WHERE user_id=1 AND sku='066573'; "
              "INSERT INTO shopping_items (user_id, sku, quantity, added_at) "
              "VALUES (1, '052484', 1, '2026-10-01')")
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"], "T0 wrong row removed must FAIL"


def test_t0_extra_add_fails():
    """Agent adds a second product too (unexplained extra delta)."""
    run_dir = clone(0, "extraadd")
    mutate_db(run_dir, "after.db",
              "INSERT INTO shopping_items (user_id, sku, quantity, added_at) "
              "VALUES (1, '066573', 1, '2026-10-01')")
    verdict = run_verifier(0, run_dir)
    assert not verdict["pass"], "T0 unexplained extra add must FAIL"


def test_t1_wrong_signup_fails():
    """Agent signs up a different account than the task names."""
    run_dir = clone(1, "wrongsignup")
    mutate_db(run_dir, "after.db",
              "UPDATE users SET email='other@test.com', name='Other Person' "
              "WHERE email='jordan.vale@test.com'")
    verdict = run_verifier(1, run_dir)
    assert not verdict["pass"], "T1 wrong signup must FAIL"


def test_t1_wrong_product_set_fails():
    """Agent adds three different products than the task names."""
    run_dir = clone(1, "wrongproducts")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='066573' WHERE user_id=5 AND sku='053711'; "
              "UPDATE shopping_items SET sku='067075' WHERE user_id=5 AND sku='051533'")
    verdict = run_verifier(1, run_dir)
    assert not verdict["pass"], "T1 wrong product set must FAIL"


def test_t3_wrong_mystore_fails():
    """Agent sets the second-closest store as My Store instead of the closest."""
    run_dir = clone(3, "wrongmystore")
    mutate_db(run_dir, "after.db",
              "UPDATE user_stores SET clientkey='131' WHERE user_id=2")
    verdict = run_verifier(3, run_dir)
    assert not verdict["pass"], "T3 wrong My Store must FAIL"


def test_t4_wrong_subscriber_fails():
    """Agent subscribes a different email than the task names."""
    run_dir = clone(4, "wrongsub")
    mutate_db(run_dir, "after.db",
              "UPDATE subscribers SET email='someone.else@example.com' "
              "WHERE email='news.hound@example.com'")
    verdict = run_verifier(4, run_dir)
    assert not verdict["pass"], "T4 wrong subscriber must FAIL"


def test_t5_subscribe_only_fails():
    """Agent subscribes but never unsubscribes (status stays 'subscribed')."""
    run_dir = clone(5, "subonly")
    mutate_db(run_dir, "after.db",
              "UPDATE subscribers SET status='subscribed' WHERE email='felice.t@example.com'")
    verdict = run_verifier(5, run_dir)
    assert not verdict["pass"], "T5 subscribe-without-unsubscribe must FAIL"


def test_t7_wrong_sku_added_fails():
    """Agent adds a different pumpkin product than the first search result."""
    run_dir = clone(7, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='084740' WHERE user_id=1 AND sku='084794'")
    verdict = run_verifier(7, run_dir)
    assert not verdict["pass"], "T7 wrong sku added must FAIL"


def test_t8_wrong_sku_added_fails():
    run_dir = clone(8, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='011364' WHERE user_id=3 AND sku='084349'")
    verdict = run_verifier(8, run_dir)
    assert not verdict["pass"], "T8 wrong sku added must FAIL"


def test_t10_wrong_mystore_fails():
    """Agent sets the first MA store (Acton) instead of Brookline as My Store."""
    run_dir = clone(10, "wrongmystore")
    mutate_db(run_dir, "after.db",
              "UPDATE user_stores SET clientkey='511' WHERE user_id=3")
    verdict = run_verifier(10, run_dir)
    assert not verdict["pass"], "T10 wrong My Store must FAIL"


def test_t11_wrong_sku_added_fails():
    run_dir = clone(11, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='063804' WHERE user_id=1 AND sku='085369'")
    verdict = run_verifier(11, run_dir)
    assert not verdict["pass"], "T11 wrong sku added must FAIL"


def test_t12_wrong_sku_added_fails():
    """r2: the spice is added and removed (net zero); an agent that leaves a
    different product in the list instead must FAIL."""
    run_dir = clone(12, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "INSERT INTO shopping_items (id, user_id, sku, quantity, added_at) "
              "VALUES (13, 1, '011364', 1, '2026-10-01')")
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"], "T12 wrong sku left in list must FAIL"


def test_t13_wrong_quantity_fails():
    """Agent increases the crispbread instead of the multigrain bread."""
    run_dir = clone(13, "wrongqty")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET quantity=1 WHERE user_id=3 AND sku='062146'; "
              "UPDATE shopping_items SET quantity=3 WHERE user_id=3 AND sku='059721'")
    verdict = run_verifier(13, run_dir)
    assert not verdict["pass"], "T13 wrong quantity change must FAIL"


def test_t14_wrong_final_rows_fails():
    """Agent adds different products than the task names."""
    run_dir = clone(14, "wrongrows")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='062144' WHERE user_id=3 AND sku='054292'; "
              "UPDATE shopping_items SET sku='071651' WHERE user_id=3 AND sku='071651'")
    verdict = run_verifier(14, run_dir)
    assert not verdict["pass"], "T14 wrong final rows must FAIL"


def test_t15_wrong_sku_added_fails():
    run_dir = clone(15, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='065191' WHERE user_id=2 AND sku='052381'")
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"], "T15 wrong sku added must FAIL"


def test_t16_wrong_mystore_fails():
    """Agent sets Bellingham - North (274) instead of Bellingham (151)."""
    run_dir = clone(16, "wrongmystore")
    mutate_db(run_dir, "after.db",
              "UPDATE user_stores SET clientkey='274' WHERE user_id=4")
    verdict = run_verifier(16, run_dir)
    assert not verdict["pass"], "T16 wrong My Store must FAIL"


def test_t17_wrong_cheddar_quantity_fails():
    """Agent decreases the cheddar instead of increasing it."""
    run_dir = clone(17, "wrongqty")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET quantity=1 WHERE user_id=2 AND sku='065191'")
    verdict = run_verifier(17, run_dir)
    assert not verdict["pass"], "T17 wrong cheddar quantity must FAIL"


def test_t18_wrong_chicken_quantity_fails():
    run_dir = clone(18, "wrongqty")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET quantity=4 WHERE user_id=2 AND sku='066563'")
    verdict = run_verifier(18, run_dir)
    assert not verdict["pass"], "T18 wrong chicken quantity must FAIL"


def test_t19_wrong_sku_added_fails():
    run_dir = clone(19, "wrongsksu")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='085369' WHERE user_id=1 AND sku='063804'")
    verdict = run_verifier(19, run_dir)
    assert not verdict["pass"], "T19 wrong sku added must FAIL"


def test_t15_artifact_story_answer_fails():
    """r2: the 404-capture artifacts are gone; an answer that still reports the
    old 'Oops!' artifact as the newest story must FAIL."""
    run_dir = clone(15, "artifactstory")
    mutate_answer(run_dir, SHORTCUT_ANSWER[15].replace(
        "The newest story is 'A Cider to Crow About' (2026-09-25)",
        "The newest story is 'Oops!' (2026-10-01)"))
    verdict = run_verifier(15, run_dir)
    assert not verdict["pass"], "T15 artifact-story answer must FAIL against r2 ground truth"


def test_t5_no_confirmation_claim_fails():
    """r2: the unsubscribe confirmation now renders; an answer that claims the
    page showed no confirmation must FAIL."""
    run_dir = clone(5, "fakeconfirm")
    mutate_answer(run_dir, SHORTCUT_ANSWER[5].replace(
        "Unsubscribing: You've been unsubscribed. felice.t@example.com has been removed "
        "from the Trader Joe's eNewsletter list - we're sorry to see you go.",
        "Unsubscribing: the page showed no confirmation message"))
    verdict = run_verifier(5, run_dir)
    assert not verdict["pass"], "T5 no-confirmation claim must FAIL against r2 ground truth"


def test_t9_wrong_desc_product_added_fails():
    """Agent adds a different product than the one linked in the first
    Desserts-only recipe's description."""
    run_dir = clone(9, "wrongdesc")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET sku='065191' WHERE user_id=3 AND sku='073946'")
    verdict = run_verifier(9, run_dir)
    assert not verdict["pass"], "T9 wrong description-product added must FAIL"


def test_t12_unremoved_spice_fails():
    """Agent increases the bisque but never removes the spice (delta mismatch)."""
    run_dir = clone(12, "unremoved")
    mutate_db(run_dir, "after.db",
              "INSERT INTO shopping_items (user_id, sku, quantity, added_at) "
              "VALUES (1, '084771', 1, '2026-10-01')")
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"], "T12 un-removed spice must FAIL"


def test_t12_wrong_bisque_quantity_fails():
    """Agent decreases the bisque instead of increasing it."""
    run_dir = clone(12, "wrongqty")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET quantity=2 WHERE user_id=1 AND sku='067075'")
    verdict = run_verifier(12, run_dir)
    assert not verdict["pass"], "T12 wrong bisque quantity must FAIL"


def test_t13_crispbread_not_removed_fails():
    """Agent increases the bread but never removes the crispbread (the row is
    still in after.db)."""
    run_dir = clone(13, "notremoved")
    mutate_db(run_dir, "after.db",
              "INSERT INTO shopping_items (id, user_id, sku, quantity, added_at) "
              "VALUES (11, 3, '059721', 2, '2026-10-01')")
    verdict = run_verifier(13, run_dir)
    assert not verdict["pass"], "T13 crispbread-not-removed must FAIL"


def test_t19_missing_increase_fails():
    """Agent adds the featured product but never increases it (qty 1 not 2)."""
    run_dir = clone(19, "noincrease")
    mutate_db(run_dir, "after.db",
              "UPDATE shopping_items SET quantity=1 WHERE user_id=1 AND sku='063804'")
    verdict = run_verifier(19, run_dir)
    assert not verdict["pass"], "T19 missing quantity increase must FAIL"
