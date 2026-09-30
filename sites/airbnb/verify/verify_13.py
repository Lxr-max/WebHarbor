#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--13 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B2): the amenity
panel now renders the canonical Hot tub checkbox, so the hot-tub filter
step is UI-reachable; the intended URL-filter truth is unchanged.

Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Asheville SERP with the hot-tub filter, the first PDP, its
    # reviews page, login, the book flow, Trips.
    check_visited_path(judge, traj, "nav_serp_hottub", r"/s/asheville/homes\?[^ ]*amenities=hot\+tub")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/39290956")
    check_visited_path(judge, traj, "nav_reviews", r"/rooms/39290956/reviews")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_book", r"/rooms/39290956/book")
    check_visited_path(judge, traj, "nav_trips", r"/trips")
    # answer ground truth
    check_answer_number(judge, answer, "hottub_count", 7)
    check_answer_any(judge, answer, "first_title",
        ["Cabin in Township 1 South Marshall",
         "Cabin/Sunrise View/Hot Tub/King Bed/No Pet Fee/5G"])
    check_answer_number(judge, answer, "first_groups", 13)
    check_answer_count_at_least(judge, answer, "first_top_tag", ["View"], 1)
    check_answer_number(judge, answer, "first_top_tag_count", 295)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_regex(judge, answer, "booked_dates", r"2026-12-06")
    check_answer_money(judge, answer, "booking_total", 1311.00)
    check_answer_number(judge, answer, "bob_bookings_total", 2)
    # stateful: bob books the filtered first result for its captured window
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 2, "stay", "39290956", None, None,
        "2026-12-06", "2026-12-11", 2, 0, 0, 0, 2, 5, 262.2,
        1311.0, 1311.0, "confirmed", "2026-09-30")], "booking_row_shape")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
