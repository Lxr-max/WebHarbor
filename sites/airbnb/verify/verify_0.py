#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--0 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B2): the amenity
panel now renders the upstream canonical amenity taxonomy intersected with
the captured corpus, so the Hot tub checkbox is present and the hot-tub
filter step is UI-reachable; the intended URL-filter truth is unchanged.

Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Lake Tahoe SERP with the exact filter set, then the hot-tub
    # variant, and the cheapest listing PDP (both visits resolve to 46330668).
    check_visited_path(judge, traj, "nav_serp", r"/s/lake-tahoe/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_price", r"/s/lake-tahoe/homes\?[^ ]*(price_max=1600|sort=price_asc)")
    check_visited_path(judge, traj, "nav_serp_hottub", r"/s/lake-tahoe/homes\?[^ ]*amenities=hot\+tub")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/46330668")
    # answer ground truth
    check_answer_number(judge, answer, "count_gf_under1600", 6)
    check_answer_phrase(judge, answer, "cheapest_name",
                        "Lake Tahoe Lovely STUDIO Marriott Timber Lodge")
    check_answer_number(judge, answer, "cheapest_rating", "4.98")
    check_answer_number(judge, answer, "count_hottub", 3)
    check_answer_money(judge, answer, "hottub_first_nightly", 123)
    check_answer_number(judge, answer, "hottub_first_groups", 11)
    check_answer_money(judge, answer, "trip_total_7n", 861.00)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
