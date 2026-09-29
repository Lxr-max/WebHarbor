"""Deterministic verifier contract tests for the 21 speedo tasks.

Covers, per task: the honest trajectory (from the reviewer's live runs, frozen
in fixtures_data.SPECS) MUST PASS; a no-op run (homepage only, empty answer,
clean DB) MUST FAIL; a knowledge-shortcut (correct answer + delta, homepage-only
navigation) MUST FAIL; a wrong answer MUST FAIL; a state-mismatch (success
claim, no DB delta) MUST FAIL for stateful tasks. Read-only tasks MUST FAIL on
a mutated after-DB. Package tampering (task_id mismatch, off-site URL, missing
screenshot, non-done trajectory, undecodable screenshot) MUST fail closed.

No LLM: snapshots are seed copies mutated through sqlite, trajectories are
written in the agent_demo/agent.py shape.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _support import (BASE, RunBuilder, copy_db, exec_sql, honest_run,  # noqa: E402
                       mutate_after_db, noop_run, run_verifier, shortcut_run,
                       task_ques, wrong_answer_run, state_mismatch_run,
                       acquire_seed)
from fixtures_data import SPECS  # noqa: E402

STATEFUL = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20}
READ_ONLY = {17}
ALL = sorted(STATEFUL | READ_ONLY)

# plausible but wrong answers per task (contradict frozen ground truth)
WRONG_ANSWERS = {
    0: "Cheapest recommended kneeskin: Women's Fastskin LZR Ignite Kneeskin Black £175.00, size 26. Order SP100009, total charged £183.99.",
    1: "Removed the Men's Endurance+ Jammer Black; the wishlist still holds the Hyperboom Jammer, the Vanquisher goggles and the Flex Bag. New wishlist count: 4.",
    2: "Order SP100009, total £54.25 with no discount applied.",
    3: "Carol's Speedo size is 34 (UK 12). Order SP100009, total £77.99 with £5.99 shipping.",
    4: "Order SP100006, status Processing, no tracking yet, charged to Mastercard ending 5309. Case reference CAS100002.",
    5: "Most expensive fitness jammer under £50: Men's Medley Logo Jammer Black/Green £31.50. Order SP100009, total £40.49.",
    6: "Adult Vanquisher 3.0 Optical Goggles Black/Grey £30.00, lens -4.5. Order SP100009, total £35.99.",
    7: "3 addresses saved; the Bristol Home address is still the default. Phone left unchanged.",
    8: "Removed the Men's Endurance+ Jammer Black and the Adult Fastskin Hyper Elite Mirrored Goggles; the wishlist still has the Openback Kneeskin and the Hyperboom Printed Medalist Swimsuit. Final wishlist count: 2.",
    9: "Final total £69.38; delivery cost £5.99 (not free).",
    10: "All colourways £33.00, none sold out in 38. Bought Blue/Green size 38. Order SP100009, total £32.39.",
    11: "All colourways £23.25, none on sale. Added the Blue colourway to Alice's wishlist.",
    12: "Goggle care: never rinse, towel-dry in the sun. FAQ: machine wash at 40. Case reference CAS100002.",
    13: "Order SP100009, Standard Delivery 3-5 working days, total £30.99.",
    14: "Saved Kids Sunny G Mariner Mirror £15.75; wishlist count 2; phone not updated.",
    15: "The code is WELCOME10; discount £1.50; order total £19.49.",
    16: "Size band 7-8 Yrs. Order SP100009, total £25.49.",
    17: "GB athletes: Adam Peaty, Ariarne Titmus, Duncan Scott, Kaylee McKeown. Motto athlete Matt Richards wore the Fastskin Intent. Cheapest Ignite Kneeskin: £90.00.",
    18: "Cheapest in-stock recommendation: Biofuse 2.0 Goggles Red £25.00. Order SP100009, total £30.99.",
    19: "2 cards saved; the old Visa ****9902 is still the default. Wishlist count 6.",
    20: "Order SP100009, Express Delivery £8.99, total £15.74.",
}


# ---------------------------------------------------------------- honest runs PASS
@pytest.mark.parametrize("n", ALL)
def test_honest_passes(tmp_path, n):
    run = honest_run(tmp_path, n)
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 0 and verdict["pass"], (
        f"task {n} honest run must PASS: {verdict['reason']}")


# ---------------------------------------------------------------- no-op FAILS
@pytest.mark.parametrize("n", ALL)
def test_noop_fails(tmp_path, n):
    run = noop_run(tmp_path, n)
    after = copy_db(tmp_path, "after.db")
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"], (
        f"task {n} no-op must FAIL (got PASS)")


# ------------------------------------------------- shortcut (right answer, no nav) FAILS
@pytest.mark.parametrize("n", ALL)
def test_shortcut_fails(tmp_path, n):
    run = shortcut_run(tmp_path, n)
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"], (
        f"task {n} knowledge-shortcut must FAIL (got PASS)")


# ---------------------------------------------------------------- wrong answer FAILS
@pytest.mark.parametrize("n", ALL)
def test_wrong_answer_fails(tmp_path, n):
    run = wrong_answer_run(tmp_path, n, WRONG_ANSWERS[n])
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"], (
        f"task {n} wrong answer must FAIL (got PASS)")


# ------------------------------------------------- state mismatch FAILS (stateful only)
@pytest.mark.parametrize("n", sorted(STATEFUL))
def test_state_mismatch_fails(tmp_path, n):
    run = state_mismatch_run(tmp_path, n)
    after = copy_db(tmp_path, "after.db")     # untouched seed
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"], (
        f"task {n} state mismatch must FAIL (got PASS)")


# ------------------------------------------------- read-only tasks FAIL on mutated DB
@pytest.mark.parametrize("n", sorted(READ_ONLY))
def test_readonly_fails_on_mutation(tmp_path, n):
    run = honest_run(tmp_path, n)
    after = mutate_after_db(tmp_path, n)      # seed copy (read-only specs carry no SQL)
    exec_sql(after, ["INSERT INTO contact_messages (case_ref, user_id, first_name,"
                     " last_name, email, category, subcategory, order_number,"
                     " address_line, postcode, message, submitted_on)"
                     " VALUES ('CAS999999', NULL, 'X', 'Y', 'x@example.com',"
                     " 'Feedback', '', '', '', '', 'tamper', '2026-09-26')"])
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"], (
        f"task {n} read-only verifier must FAIL on mutated after-DB (got PASS)")


# ---------------------------------------------------------------- package tampering
@pytest.mark.parametrize("n", [0, 9, 17])
def test_tampered_task_id_fails(tmp_path, n):
    run = honest_run(tmp_path, n)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["task_id"] = "Speedo--99"
    (run / "trajectory.json").write_text(json.dumps(traj))
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"]


@pytest.mark.parametrize("n", [0, 5, 12])
def test_offsite_url_fails(tmp_path, n):
    run = honest_run(tmp_path, n)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["steps"][1]["url_after"] = "https://speedo.com/products/evil"
    (run / "trajectory.json").write_text(json.dumps(traj))
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"]


@pytest.mark.parametrize("n", [1, 7, 19])
def test_missing_screenshot_fails(tmp_path, n):
    run = honest_run(tmp_path, n)
    traj = json.loads((run / "trajectory.json").read_text())
    ref = traj["steps"][0]["screenshot_after"]
    (run / "screenshots" / ref).unlink()
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"]


@pytest.mark.parametrize("n", [3, 15])
def test_not_terminated_fails(tmp_path, n):
    run = honest_run(tmp_path, n)
    traj = json.loads((run / "trajectory.json").read_text())
    traj["terminated"] = False
    traj["termination_reason"] = None
    (run / "trajectory.json").write_text(json.dumps(traj))
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"]


@pytest.mark.parametrize("n", [6, 13])
def test_undecodable_screenshot_fails(tmp_path, n):
    run = honest_run(tmp_path, n)
    traj = json.loads((run / "trajectory.json").read_text())
    ref = traj["steps"][0]["screenshot_after"]
    (run / "screenshots" / ref).write_bytes(b"\x89PNG\r\n\x1a\nGARBAGE")
    after = mutate_after_db(tmp_path, n)
    code, verdict = run_verifier(n, run, after)
    assert code == 1 and not verdict["pass"]


# ---------------------------------------------------------------- adversarial deltas
def test_wrong_product_delta_fails(tmp_path):
    """Right navigation + right answer text, but the DB delta is for the wrong
    product (a different order_item): must FAIL."""
    run = honest_run(tmp_path, 0)
    after = mutate_after_db(tmp_path, 0)
    # corrupt the order item: wrong product, wrong size
    exec_sql(after, ["UPDATE order_items SET product_name = 'X', size = '30'"])
    code, verdict = run_verifier(0, run, after)
    assert code == 1 and not verdict["pass"]


def test_extra_table_delta_fails(tmp_path):
    """Honest delta PLUS an unrelated row change elsewhere: must FAIL."""
    run = honest_run(tmp_path, 2)
    after = mutate_after_db(tmp_path, 2)
    exec_sql(after, ["UPDATE users SET name = 'Mallory' WHERE id = 4"])
    code, verdict = run_verifier(2, run, after)
    assert code == 1 and not verdict["pass"]


def test_tainted_initial_db_fails(tmp_path):
    """initial.db that is not the frozen seed: must FAIL closed."""
    run = honest_run(tmp_path, 1)
    initial = copy_db(tmp_path, "initial.db")
    exec_sql(initial, ["UPDATE users SET name = 'Fake' WHERE id = 1"])
    after = mutate_after_db(tmp_path, 1)
    code, verdict = run_verifier(1, run, after, initial_db=initial)
    assert code == 1 and not verdict["pass"]
