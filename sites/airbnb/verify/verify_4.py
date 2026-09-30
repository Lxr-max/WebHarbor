#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--4 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B4): the
experience PDP now renders the captured guest_requirements payload as
structured text, so the minimum guest age reads the frozen truth (21 for
this experience) instead of the old "any".

Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Austin experiences SERP, the Cooking category, the detail
    # page, login, the wishlist page, the book flow, Trips, back to the SERP.
    check_visited_path(judge, traj, "nav_exp_serp", r"/s/experiences\?[^ ]*city=austin")
    check_visited_path(judge, traj, "nav_cooking", r"/s/experiences\?[^ ]*category=Cooking")
    check_visited_path(judge, traj, "nav_exp", r"/experiences/6190940")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_book", r"/experiences/6190940/book")
    check_visited_path(judge, traj, "nav_trips", r"/trips")
    # answer ground truth
    check_answer_number(judge, answer, "cooking_count", 1)
    check_answer_phrase(judge, answer, "exp_name",
                        "Craft cocktails with an award-winning mixologist")
    check_answer_money(judge, answer, "price_per_guest", 99)
    check_answer_number(judge, answer, "min_age", 21)
    check_answer_number(judge, answer, "agenda_stops", 4)
    check_answer_money(judge, answer, "total", 198.00)
    check_answer_regex(judge, answer, "booked_date", r"2026-10-04")
    check_answer_number(judge, answer, "austin_total", 20)
    # stateful: bob saves the experience + books it for 2 guests
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, 2, None, "6190940", "2026-09-30")], "bob_save")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 2, "experience", None, "6190940",
        "2026-10-04T17:30:00-05:00", None, None, 2, 0, 0, 0, 2,
        None, None, 198.0, 198.0, "confirmed", "2026-09-30")],
        "booking_row_shape")
    check_only_tables_changed(judge, initial, after,
                              {"wishlist_items", "bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
