#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--17 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


No premise gaps on the honest path (the walk completes cleanly).

Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Lake Tahoe SERP with Guest favorite, the clear, the second
    # listing PDP, its reviews page, login, the wishlist page.
    check_visited_path(judge, traj, "nav_serp_gf", r"/s/lake-tahoe/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_all", r"/s/lake-tahoe/homes(\?|$)")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1755384460282754920")
    check_visited_path(judge, traj, "nav_reviews", r"/rooms/1755384460282754920/reviews")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    # answer ground truth
    check_answer_number(judge, answer, "gf_count", 8)
    check_answer_phrase(judge, answer, "second_name", "Queen double")
    check_answer_number(judge, answer, "second_rating", "4.86")
    check_answer_count_at_least(judge, answer, "explore_dests",
        ["San Francisco", "San Jose"], 2)
    check_answer_count_at_least(judge, answer, "top_tag", ["Cleanliness"], 1)
    check_answer_number(judge, answer, "top_tag_count", 13)
    check_answer_phrase(judge, answer, "first_reviewer_location", "Moscow, Idaho")
    check_answer_number(judge, answer, "default_wishlist_items", 1)
    # stateful: dana's save creates her default wishlist + one saved item
    check_rows_added(judge, initial, after, "wishlists", [(
        None, 4, "Saved", None, "2026-09-30")], "wishlist_row")
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, 6, "1755384460282754920", None, "2026-09-30")], "wishlist_item_row")
    check_only_tables_changed(judge, initial, after, {"wishlists", "wishlist_items"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
