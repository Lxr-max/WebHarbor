#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--3 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTES (contribution fix round, review findings B2/H1/M3 +
depth): (a) the SERP cards now render each listing's review count, so
"the listing whose card shows the largest review count" is card-readable;
(b) the amenity panel now renders the canonical Hot tub checkbox (B2), so
the hot-tub filter step is UI-reachable; (c) the unanswerable "average
cleanliness rating" ask (the target's category_ratings list is empty in
the capture) was replaced by "the third review tag with its count";
(d) the task was deepened with a second-filtered-result question point
(title + nightly rate of the second hot-tub listing); (e) the target
listing (39290956) is already in Bob's seed wishlist, so the save is a
silent no-op (no state delta) — the PDP now shows the Saved state.

Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Asheville SERP, the top-reviewed PDP + its reviews page,
    # the hot-tub SERP variant, the filtered first PDP, login.
    check_visited_path(judge, traj, "nav_serp", r"/s/asheville/homes")
    check_visited_path(judge, traj, "nav_top_pdp", r"/rooms/27156940")
    check_visited_path(judge, traj, "nav_reviews", r"/rooms/27156940/reviews")
    check_visited_path(judge, traj, "nav_serp_hottub", r"/s/asheville/homes\?[^ ]*amenities=hot\+tub")
    check_visited_path(judge, traj, "nav_second_filtered", r"/rooms/1743048462809358991")
    check_visited_path(judge, traj, "nav_login", r"/login")
    # answer ground truth (top-reviewed Asheville listing)
    check_answer_phrase(judge, answer, "top_name",
                        "Cottage in the Trees- Walk Downtown AVL- Hot Tub")
    check_answer_number(judge, answer, "top_reviews", 904)
    check_answer_phrase(judge, answer, "first_reviewer", "Dylan")
    check_answer_count_at_least(judge, answer, "top_tag", ["Location"], 1)
    check_answer_number(judge, answer, "top_tag_count", 476)
    check_answer_count_at_least(judge, answer, "third_tag", ["Walkability"], 1)
    check_answer_number(judge, answer, "third_tag_count", 334)
    check_answer_number(judge, answer, "hottub_count", 7)
    check_answer_money(judge, answer, "saved_nightly", 262.20)
    check_answer_any(judge, answer, "second_title",
                     ["Cabin in Hendersonville"])
    check_answer_money(judge, answer, "second_nightly", 282.00)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
