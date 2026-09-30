#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--15 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTES (contribution fix round, review finding M2 + depth):
(a) the unanswerable "first three amenity group titles" ask (the target's
captured amenity groups list is empty — amenities [] despite
amenity_count 66; the PDP now states the group details weren't captured)
was replaced by "its maximum guest capacity and its check-in time window"
(2 guests; house-rules check-in 2:00 PM - 11:00 PM); (b) the task was
deepened with a pool-filter question point (7 Guest favorites remain
with a pool filter applied).

Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Scottsdale SERP with Guest favorite + price_desc, the most
    # expensive PDP + reviews, the second most expensive PDP + reviews.
    check_visited_path(judge, traj, "nav_serp", r"/s/scottsdale/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_sorted", r"/s/scottsdale/homes\?[^ ]*sort=price_desc")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/3423570")
    check_visited_path(judge, traj, "nav_reviews", r"/rooms/3423570/reviews")
    check_visited_path(judge, traj, "nav_second_pdp", r"/rooms/688342926601653244")
    check_visited_path(judge, traj, "nav_second_reviews", r"/rooms/688342926601653244/reviews")
    check_visited_path(judge, traj, "nav_serp_pool", r"/s/scottsdale/homes\?[^ ]*amenities=pool")
    # answer ground truth
    check_answer_any(judge, answer, "name",
        ["Casita Bonita  in N. Scottsdale,AZ by Troon & Golf",
         "Casita Bonita in N. Scottsdale,AZ by Troon & Golf"])
    check_answer_money(judge, answer, "trip_price", 1313.00)
    check_answer_number(judge, answer, "review_count", 458)
    check_answer_number(judge, answer, "capacity", 2)
    check_answer_regex(judge, answer, "checkin_from", r"2:00\s*PM")
    check_answer_regex(judge, answer, "checkin_until", r"11:00\s*PM")
    check_answer_count_at_least(judge, answer, "top_tag", ["Hospitality"], 1)
    check_answer_number(judge, answer, "top_tag_count", 282)
    check_answer_phrase(judge, answer, "first_reviewer", "Jeffry")
    check_answer_any(judge, answer, "second_name",
        ["Scottsdale Home OldTown w 3bth & 3bdrm heated pool"])
    check_answer_money(judge, answer, "second_nightly", 255.60)
    check_answer_phrase(judge, answer, "second_first_reviewer", "Tom")
    check_answer_number(judge, answer, "pool_count", 7)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
