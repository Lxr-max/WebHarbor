#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--16 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B2): the amenity
panel now renders the canonical Hot tub checkbox, so the hot-tub filter
step is UI-reachable; the intended URL-filter truth is unchanged.

Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: LA SERP with the hot-tub filter, the cheapest PDP, signup,
    # the book flow, Trips, the cancel, the wishlist page.
    check_visited_path(judge, traj, "nav_serp_hottub",
                       r"/s/los-angeles/homes\?[^ ]*amenities=hot\+tub")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1692465124519066586")
    check_visited_path(judge, traj, "nav_signup", r"/signup")
    check_visited_path(judge, traj, "nav_book", r"/rooms/1692465124519066586/book")
    check_visited_path(judge, traj, "nav_trips", r"/trips")
    check_visited_path(judge, traj, "nav_booking_page", r"/bookings/HM[A-Z0-9]{8}")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    # answer ground truth (the task never asks to save anything to a wishlist:
    # the fresh account's default wishlist stays EMPTY)
    check_answer_number(judge, answer, "hottub_count", 3)
    check_answer_any(judge, answer, "cheapest_title",
        ["Apartment in Vernon", "DTLA Highrise Retreat w/ Private Balcony"])
    check_answer_money(judge, answer, "cheapest_nightly", 280.20)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_money(judge, answer, "booking_total", 1401.00)
    check_answer_phrase(judge, answer, "final_status", "cancelled")
    check_answer_number(judge, answer, "default_wishlist_items", 0)
    # stateful: new user + default wishlist (no items) + one booking (cancelled)
    check_rows_added(judge, initial, after, "users", [(
        None, "casey.t@test.com", None, None, "2026-09-30")], "user_row")
    check_rows_added(judge, initial, after, "wishlists", [(
        None, 5, "Saved", None, "2026-09-30")], "wishlist_row")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 5, "stay", "1692465124519066586", None, None,
        "2026-12-26", "2026-12-31", 2, 0, 0, 0, 2, 5, 280.2,
        1401.0, 1401.0, "cancelled", "2026-09-30")],
        "booking_row_shape")
    check_only_tables_changed(judge, initial, after,
                              {"users", "wishlists", "bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
