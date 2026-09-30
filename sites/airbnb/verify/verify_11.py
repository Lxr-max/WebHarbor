#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--11 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


No premise gaps on the honest path (signup-first booking walks cleanly).

Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: signup, Miami SERP with Guest favorite + price_asc, the
    # cheapest PDP, the book flow, the wishlist page.
    check_visited_path(judge, traj, "nav_signup", r"/signup")
    check_visited_path(judge, traj, "nav_serp", r"/s/miami/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_sorted", r"/s/miami/homes\?[^ ]*sort=price_asc")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1538398334303390660")
    check_visited_path(judge, traj, "nav_book", r"/rooms/1538398334303390660/book")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    # answer ground truth
    check_answer_phrase(judge, answer, "name", "Miami Room Near Airport, Cruise Port")
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_money(judge, answer, "total", 385.00)
    check_answer_phrase(judge, answer, "wishlist_name", "Saved")
    check_answer_number(judge, answer, "wishlist_items", 1)
    # stateful: new user + default wishlist + saved item + one booking
    check_rows_added(judge, initial, after, "users", [(
        None, "sam.r@test.com", None, None, "2026-09-30")], "user_row")
    check_rows_added(judge, initial, after, "wishlists", [(
        None, 5, "Saved", None, "2026-09-30")], "wishlist_row")
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, None, "1538398334303390660", None, "2026-09-30")], "wishlist_item_row")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 5, "stay", "1538398334303390660", None, None,
        "2026-10-18", "2026-10-23", 2, 0, 0, 0, 2, 5, 77.0,
        385.0, 385.0, "confirmed", "2026-09-30")], "booking_row_shape")
    check_only_tables_changed(judge, initial, after,
                              {"users", "wishlists", "wishlist_items", "bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
