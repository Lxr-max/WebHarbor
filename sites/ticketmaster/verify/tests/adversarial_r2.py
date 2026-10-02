#!/usr/bin/env python3
"""Extra adversarial negatives for the r2 contract (beyond the frozen suite).

Each case builds an agent-shaped run dir and asserts the verifier FAILS:
  A. T0 accessible purchase — the old dual-reading: buy the cheaper
     Accessible listing and report it. The re-anchored wording pins
     "Standard Admission", so this must FAIL.
  B. T17 former tie — buy Sec 202 Row F at $78.43 (the pre-de-tie price)
     and report it. The seed de-tied the minimum (202 F is now $78.45), so
     this must FAIL on both the DB row and the answer.
  C. T5 wrong winner — report the Oct 29 show (the old accessible-anchored
     winner) with the old total. Must FAIL.
  D. T13 partial answer — report only the qty-3 breakdown, omitting the
     qty-1 and section-118 parts. Must FAIL (answer face expanded).
  E. T16 wrong comparison — claim TSO is rated higher. Must FAIL.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import RunBuilder, BASE, copy_db, exec_sql, run_verifier  # noqa: E402
from fixtures_data import _purchase  # noqa: E402

results = []


def build_and_run(name, task_no, urls, inputs, answer, mutations, expect_pass=False):
    root = Path('/tmp/tm_adv') / name
    if root.exists():
        import shutil
        shutil.rmtree(root)
    root.mkdir(parents=True)
    tid = f"Ticketmaster--{task_no}"
    b = RunBuilder(root, tid)
    pending = {}
    for idx, text in inputs:
        pending.setdefault(idx, []).append(text)
    for i, u in enumerate(urls):
        b.add_step("navigate", u)
        for text in pending.get(i, ()):
            b.add_input(text)
    b.finish(answer)
    copy_db(root, "after.db")
    if mutations:
        exec_sql(root / "after.db", mutations)
    copy_db(root, "initial.db")
    res = run_verifier(task_no, root, expect_pass=expect_pass)
    results.append((name, res["pass"], res["reason"]))
    print(f"[{name}] pass={res['pass']} (expected {expect_pass}) reason={res['reason'][:110]}")


# A. T0: buy the Accessible listing (old dual-reading) -> must FAIL
build_and_run(
    "A_t0_accessible_purchase", 0,
    [BASE + u for u in (
        "/signin", "/member", "/search?q=knicks+pistons",
        "/event/3B006511E91D862B",
        "/event/3B006511E91D862B/tickets?listing=7060&qty=2",
        "/checkout", "/checkout?step=payment", "/checkout?step=review",
        "/order-confirmation/4A934621D5B765", "/member/orders")],
    [(0, "alice.j@test.com"), (0, "TestPass123!"), (1, "knicks pistons")],
    "Order confirmed: order 4A934621D5B765, Sec BALC Row W (Accessible), "
    "all-in total $333.18 for 2 tickets.",
    _purchase(7, "4A934621D5B765", 1, "3B006511E91D862B", 7060, "BALC",
              "Balcony", "W", 2, 166.59, 242.14, 91.04, 333.18,
              "4242", "Visa", "NULL", 0),
)

# B. T17: buy the former tie 202 F at the old price -> must FAIL
build_and_run(
    "B_t17_former_tie", 17,
    [BASE + u for u in (
        "/signin", "/member", "/search?q=weezer+the+gathering",
        "/event/3000646DEDC399B4",
        "/event/3000646DEDC399B4?qty=4&price_max=&type=&sort=lowest",
        "/event/3000646DEDC399B4/tickets?listing=34934&qty=4",
        "/checkout", "/checkout?step=payment", "/checkout?step=review",
        "/order-confirmation/56D82CFDA76B40", "/member/orders")],
    [(0, "alice.j@test.com"), (0, "TestPass123!"), (1, "weezer the gathering")],
    "Order confirmed in My Account: order 56D82CFDA76B40, Sec 202 Row F, "
    "4 tickets together, total $313.72.",
    _purchase(7, "56D82CFDA76B40", 1, "3000646DEDC399B4", 34934, "202",
              "Upper Level 202", "F", 4, 78.43, 228.00, 85.72, 313.72,
              "4242", "Visa", "NULL", 0),
)

# C. T5: report the Oct 29 show with the old accessible-anchored total -> FAIL
build_and_run(
    "C_t5_wrong_winner", 5,
    [BASE + u for u in (
        "/discover/concerts",
        "/discover/concerts?sub=&city=Las+Vegas&date_from=2026-10-29&date_to=2026-11-01&price_max=&sort=price",
        "/event/170064550781E861")],
    [(1, "2026-10-29"), (1, "2026-11-01")],
    "The cheapest Music event in that window is Metallica: Life Burns Faster "
    "on Oct 29, 2026 (a Thursday). Two of the cheapest available tickets come "
    "to $161.52 all-in; the Oct 31 show is a Saturday.",
    None,
)

# D. T13: only the qty-3 breakdown, missing the qty-1 and 118 parts -> FAIL
build_and_run(
    "D_t13_partial_answer", 13,
    [BASE + u for u in (
        "/", "/search?q=power+to+the+people", "/event/150064B8F802C6F9",
        "/event/150064B8F802C6F9/tickets?listing=1189&qty=3")],
    [(1, "power to the people")],
    "For 3 Standard Admission tickets in section 202, row G: face value "
    "$138.00, service fees $51.90, order total $189.90.",
    None,
)

# E. T16: claim TSO is rated higher -> FAIL
build_and_run(
    "E_t16_wrong_comparison", 16,
    [BASE + u for u in (
        "/", "/search?q=trans-siberian+orchestra", "/artist/780815",
        "/search?q=wicked", "/artist/864373")],
    [(1, "trans-siberian orchestra"), (3, "wicked")],
    "Trans-Siberian Orchestra: rating 4.6 from 1617 reviews, 18 events in "
    "December 2026, first Dec 02 at Bridgestone Arena. Wicked (Touring): 4.7 "
    "from 936 reviews, 0 events in 2026. Fans rate Trans-Siberian Orchestra "
    "higher.",
    None,
)

print()
ok = all(not p for _, p, _ in results)
for name, p, reason in results:
    print(f"  {name}: pass={p} (expected False)")
print("ALL ADVERSARIAL NEGATIVES CORRECTLY REJECTED" if ok else "FALSE POSITIVE DETECTED")
sys.exit(0 if ok else 1)
