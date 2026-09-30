#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--2 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding H1): the SERP
cards now render each listing's review count, so "the listing whose card
shows the most reviews" is card-readable; the gated target is unchanged
(1439891422884830295, 890 reviews).

Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: signup, Miami SERP, the most-reviewed PDP, the second card
    # PDP, the wishlist page.
    check_visited_path(judge, traj, "nav_signup", r"/signup")
    check_visited_path(judge, traj, "nav_serp", r"/s/miami/homes")
    check_visited_path(judge, traj, "nav_top_pdp", r"/rooms/1439891422884830295")
    check_visited_path(judge, traj, "nav_second_pdp", r"/rooms/1780536634115435633")
    check_visited_path(judge, traj, "nav_wishlist", r"/wishlist")
    # answer ground truth
    check_answer_count_at_least(judge, answer, "saved_names",
        ["Prime Spot Queen bed, Collins Av",
         "South Beach King Room | Boutique Hotel"], 2)
    check_answer_number(judge, answer, "saved_items", 2)
    check_answer_number_absent(judge, answer, "not_three_items", 3)
    # stateful: new user + new wishlist + two wishlist items
    check_rows_added(judge, initial, after, "users", [(
        None, "runner2@test.com", None, None, "2026-09-30")], "user_row")
    check_rows_added(judge, initial, after, "wishlists", [(
        None, 5, "Saved", 1, "2026-09-30"), (
        None, 5, "Beach trip", None, "2026-09-30")], "wishlist_rows")
    check_rows_added(judge, initial, after, "wishlist_items", [(
        None, None, "1439891422884830295", None, "2026-09-30"), (
        None, None, "1780536634115435633", None, "2026-09-30")], "wishlist_item_rows")
    check_only_tables_changed(judge, initial, after,
                              {"users", "wishlists", "wishlist_items"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
