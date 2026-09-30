#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--8 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTES (contribution fix round, review findings B3/B4): (a)
the Experiences search now renders a destination selector, so "browse Los
Angeles experiences" is UI-reachable; (b) the experience PDP now renders
the captured guest_requirements payload as structured text, so the
minimum guest age reads the frozen truth (15 for this experience).

R3 NOTE (review r2, B4 residual fixed): the agenda stop titles now render
their localizedString instead of the upstream dict repr, so the
max_agenda_first question point reads the clean frozen truth
("Step into the cockpit") straight off the page — no KNOWN-GAP remains.

Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, new_bookings,
    check_answer_has_new_booking_code, run_verifier, BOOKING_CODE_RX,
)

TASK_ID = "Airbnb--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: LA experiences SERP (sorted), the most expensive detail,
    # the second most expensive, login, the wishlist page.
    check_visited_path(judge, traj, "nav_exp_serp", r"/s/experiences\?[^ ]*city=los-angeles")
    check_visited_path(judge, traj, "nav_exp_sorted", r"/s/experiences\?[^ ]*sort=price_desc")
    check_visited_path(judge, traj, "nav_exp_max", r"/experiences/109978")
    check_visited_path(judge, traj, "nav_exp_second", r"/experiences/7287785")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    # answer ground truth
    check_answer_number(judge, answer, "la_count", 20)
    check_answer_phrase(judge, answer, "max_name",
                        "Fly an airplane over LA\u2019s epic landmarks")
    check_answer_any(judge, answer, "max_category", ["Flying"])
    check_answer_money(judge, answer, "max_price", 290)
    check_answer_number(judge, answer, "max_rating", "4.97")
    check_answer_number(judge, answer, "max_rating_count", 1606)
    check_answer_phrase(judge, answer, "max_agenda_first", "Step into the cockpit")
    check_answer_number(judge, answer, "max_min_age", 15)
    check_answer_phrase(judge, answer, "second_name",
                        "Eat a 5-course Haitian meal with @haitiankokitchen")
    check_answer_money(judge, answer, "second_price", 165)
    check_answer_number(judge, answer, "second_rating_count", 2)
    check_answer_phrase(judge, answer, "wishlist_name", "Saved")
    check_answer_number(judge, answer, "bob_trips", 1)
    # stateful: bob saves the most expensive experience to his default wishlist
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, 2, None, "109978", "2026-09-30")], "bob_save")
    check_only_tables_changed(judge, initial, after, {"wishlist_items"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
