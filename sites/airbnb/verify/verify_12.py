#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--12 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTES (contribution fix round, review findings B2 + depth):
(a) the amenity panel now renders the canonical Pool checkbox, so the
pool-filter step is UI-reachable; (b) the task was deepened with a
cheapest-pool-listing question point (the cheapest Nashville pool listing
by nightly rate, 1755402107627425094 at $164.20/night).

Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Nashville SERP with the Superhost filter, the first
    # Superhost PDP + its reviews page, the clear, the pool SERP variant,
    # the pool-first PDP + its reviews page.
    check_visited_path(judge, traj, "nav_serp_sh", r"/s/nashville/homes\?[^ ]*superhost=1")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/1766059769369426427")
    check_visited_path(judge, traj, "nav_reviews", r"/rooms/1766059769369426427/reviews")
    check_visited_path(judge, traj, "nav_serp_clear", r"/s/nashville/homes(\?|$)")
    check_visited_path(judge, traj, "nav_serp_pool", r"/s/nashville/homes\?[^ ]*amenities=pool")
    check_visited_path(judge, traj, "nav_pool_pdp", r"/rooms/1371243776626861688")
    check_visited_path(judge, traj, "nav_pool_reviews", r"/rooms/1371243776626861688/reviews")
    check_visited_path(judge, traj, "nav_cheapest_pool", r"/rooms/1755402107627425094")
    # answer ground truth
    check_answer_number(judge, answer, "superhost_count", 2)
    check_answer_any(judge, answer, "first_title",
        ["Condo in Downtown Nashville",
         "Riverview Condo - Walk to Downtown + Free Parking"])
    check_answer_phrase(judge, answer, "host_name", "Amy")
    check_answer_phrase(judge, answer, "years_hosting", "5 years hosting")
    check_answer_count_at_least(judge, answer, "checkin_window", ["Check-in after 4:00"], 1)
    check_answer_count_at_least(judge, answer, "top_tag", ["Walkability"], 1)
    check_answer_number(judge, answer, "top_tag_count", 2)
    check_answer_any(judge, answer, "pool_first_title",
        ["Apartment in Downtown Nashville",
         "Ultimate Retreat! Glam Bar, Broadway, Heated Pool"])
    check_answer_money(judge, answer, "pool_first_nightly", 199.40)
    check_answer_phrase(judge, answer, "pool_first_reviewer", "Susan")
    check_answer_money(judge, answer, "cheapest_pool_nightly", 164.20)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
