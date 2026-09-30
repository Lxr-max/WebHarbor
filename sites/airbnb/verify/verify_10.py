#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--10 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding M5): the wishlist
cards now show each saved stay's market alongside its title, so "the saved
Scottsdale stay" is identifiable from the wishlists page.

R3 RE-FREEZE NOTE (review r2, T10 depth re-anchor): M5 made both saved-stay
identifications free (card markets), dropping the honest minimal walk to 14
steps. The task now books the Scottsdale stay for 3 guests (the GUESTS select
defaults to 2, so the pick is a genuinely required gesture) and reports the
guest count from the trip page — an honest 15-step chain, no padding.

Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: login, the wishlists page (before/after the remove), Trips,
    # the Scottsdale reviews page, the re-booking flow.
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlists", r"/wishlist")
    check_visited_path(judge, traj, "nav_trips", r"/trips")
    check_visited_path(judge, traj, "nav_scott_reviews",
                       r"/rooms/1561618833129263447/reviews")
    check_visited_path(judge, traj, "nav_rebook", r"/rooms/1561618833129263447/book")
    # answer ground truth (alice's saved items before the removal)
    check_answer_number(judge, answer, "saved_before", 3)
    check_answer_count_at_least(judge, answer, "saved_names_before",
        ["Giant Paddleboarding in Downtown Austin's Springs",
         "Minutes to OdySea Aquarium + Pool & Fitness Center",
         "South Tahoe Bungalow Close Walk to Everything"], 3)
    check_answer_number(judge, answer, "saved_after", 2)
    check_answer_count_at_least(judge, answer, "saved_names_after",
        ["Giant Paddleboarding in Downtown Austin's Springs",
         "Minutes to OdySea Aquarium + Pool & Fitness Center"], 2)
    check_answer_count_at_least(judge, answer, "trips_codes",
                                 ["HMSEED001", "HMSEED002"], 2)
    check_answer_any(judge, answer, "trip1_status", ["confirmed", "Confirmed"])
    check_answer_any(judge, answer, "trip2_status", ["cancelled", "Cancelled"])
    check_answer_count_at_least(judge, answer, "scott_top_tag", ["Cleanliness"], 1)
    # stateful: the Tahoe wishlist item is removed; one new booking is created
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "new_code")
    check_rows_removed(judge, initial, after, "wishlist_items", [(
        1, 1, "13434357", None, "2026-09-30")], "tahoe_item_removed")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 1, "stay", "1561618833129263447", None, None,
        "2026-10-25", "2026-10-30", 3, 0, 0, 0, 3, 5, 208.74,
        1043.7, 1043.7, "confirmed", "2026-09-30")], "booking_row_shape")
    check_answer_money(judge, answer, "rebook_total", 1043.70)
    check_answer_number(judge, answer, "rebook_guests", 3)
    check_answer_regex(judge, answer, "rebook_dates", r"2026-10-25")
    check_only_tables_changed(judge, initial, after,
                              {"wishlist_items", "bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
