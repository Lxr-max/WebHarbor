#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--5 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B2): the amenity
panel now renders the canonical Pool checkbox, so the pool-filter step is
UI-reachable; the intended URL-filter truth is unchanged.

Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Nashville SERP with the Guest-favorite filter, the pool
    # variant, the price_desc sort, the priciest and cheapest PDPs.
    check_visited_path(judge, traj, "nav_serp_gf", r"/s/nashville/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_pool", r"/s/nashville/homes\?[^ ]*amenities=pool")
    check_visited_path(judge, traj, "nav_serp_desc", r"/s/nashville/homes\?[^ ]*sort=price_desc")
    check_visited_path(judge, traj, "nav_first_pool", r"/rooms/1371243776626861688")
    check_visited_path(judge, traj, "nav_priciest", r"/rooms/[0-9]+")
    # answer ground truth
    check_answer_number(judge, answer, "gf_count", 6)
    check_answer_number(judge, answer, "gf_pool_count", 3)
    check_answer_any(judge, answer, "first_title",
        ["Apartment in Downtown Nashville",
         "Ultimate Retreat! Glam Bar, Broadway, Heated Pool"])
    check_answer_money(judge, answer, "first_nightly", 199.40)
    check_answer_phrase(judge, answer, "priciest_name",
                        "11 Beds Hot Tub Game Room Rooftop Grill")
    check_answer_money(judge, answer, "priciest_total", 1143.00)
    check_answer_phrase(judge, answer, "priciest_host", "Chris")
    check_answer_number(judge, answer, "cheapest_reviews", 5)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
