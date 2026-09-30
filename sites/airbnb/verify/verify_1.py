#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--1 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B2): the amenity
panel now renders the canonical Pool checkbox, so the pool-filter step is
UI-reachable; the intended URL-filter truth is unchanged.

Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: login, the filtered Scottsdale SERP, the first result PDP,
    # the book flow, the booking page, Trips and the cancel.
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_serp", r"/s/scottsdale/homes\?[^ ]*instant_book=1")
    check_visited_path(judge, traj, "nav_serp_pool", r"/s/scottsdale/homes\?[^ ]*amenities=pool")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1561618833129263447")
    check_visited_path(judge, traj, "nav_book", r"/rooms/1561618833129263447/book")
    check_visited_path(judge, traj, "nav_booking_page", r"/bookings/HM[A-Z0-9]{8}")
    check_visited_path(judge, traj, "nav_trips", r"/trips")
    check_visited_path(judge, traj, "nav_booking_page", r"/bookings/HM[A-Z0-9]{8}")
    # stateful: exactly one new stay booking for alice (user_id 1), later cancelled
    added = new_bookings(judge, initial, after)
    code = check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 1, "stay", "1561618833129263447", None, None,
        "2026-10-25", "2026-10-30", 2, 0, 0, 0, 2, 5, 208.74,
        1043.7, 1043.7, "cancelled", "2026-09-30")],
        "booking_row_shape")
    check_answer_money(judge, answer, "booking_total", 1043.70)
    check_answer_phrase(judge, answer, "final_status", "cancelled")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
