#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--6 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTE (review finding H2): the Winter cabins wishlist fixture
was re-ordered (reverse insertion, like upstream's most-recently-saved-
first wishlist display) so the FIRST Winter cabins entry is now the South
Tahoe Bungalow (13434357), which carries a captured quote window
(2026-10-04 to 2026-10-09, 5 nights, $1,154 trip price) and is bookable;
the previous first entry ("Queen double", 1755384460282754920) has no
captured window at all and is now the second entry. The booking gates
below are the re-frozen truth of that fixed flow.

Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: login, the wishlists page, both Winter cabins PDPs,
    # the second listing's reviews page, and the book flow for the first.
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlists", r"/wishlist")
    check_visited_path(judge, traj, "nav_first_winter", r"/rooms/13434357")
    check_visited_path(judge, traj, "nav_second_winter", r"/rooms/1755384460282754920")
    check_visited_path(judge, traj, "nav_second_reviews", r"/rooms/1755384460282754920/reviews")
    check_visited_path(judge, traj, "nav_book", r"/rooms/13434357/book")
    check_visited_path(judge, traj, "nav_booking_page", r"/bookings/HM[A-Z0-9]{8}")
    # answer ground truth
    check_answer_number(judge, answer, "wishlist_count", 2)
    check_answer_count_at_least(judge, answer, "wishlist_names",
        ["Winter cabins", "NYC weekend"], 2)
    check_answer_phrase(judge, answer, "first_name",
                        "South Tahoe Bungalow Close Walk to Everything")
    check_answer_money(judge, answer, "first_nightly", 230.80)
    check_answer_number(judge, answer, "first_rating", "4.96")
    check_answer_any(judge, answer, "second_hot_tub",
        ["no hot tub", "does not offer a hot tub", "no, it does not",
         "without a hot tub"])
    check_answer_count_at_least(judge, answer, "second_top_tag", ["Cleanliness"], 1)
    check_answer_number(judge, answer, "second_top_tag_count", 13)
    check_answer_number(judge, answer, "nyc_items", 2)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added,
                                      "booking_code")
    check_answer_money(judge, answer, "booking_total", 1154.00)
    check_answer_regex(judge, answer, "booked_dates", r"2026-10-04")
    check_answer_regex(judge, answer, "booked_dates_out", r"2026-10-09")
    # stateful: dana books the first Winter cabins listing for its captured
    # window with 2 guests
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 4, "stay", "13434357", None, None,
        "2026-10-04", "2026-10-09", 2, 0, 0, 0, 2, 5, 230.8,
        1154.0, 1154.0, "confirmed", "2026-09-30")], "booking_row_shape")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
