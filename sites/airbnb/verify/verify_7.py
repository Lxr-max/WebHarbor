#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--7 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding M1): the
mid-booking login bounce is fixed (relative `next`), so the confirm round
trip returns to the book page without browser-back recovery.

Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: New York SERP with Guest favorite + price_asc, the cheapest
    # PDP, the book flow (with the broken-login recovery), login.
    check_visited_path(judge, traj, "nav_serp", r"/s/new-york/homes\?[^ ]*guest_favorite=1")
    check_visited_path(judge, traj, "nav_serp_sorted", r"/s/new-york/homes\?[^ ]*sort=price_asc")
    check_visited_path(judge, traj, "nav_pdp", r"/rooms/759618126064467893")
    check_visited_path(judge, traj, "nav_book", r"/rooms/759618126064467893/book")
    check_visited_path(judge, traj, "nav_login", r"/login")
    # answer ground truth
    check_answer_phrase(judge, answer, "name", "Cozy bedroom with city views")
    check_answer_money(judge, answer, "nightly", 110)
    check_answer_money(judge, answer, "captured_total", 550.00)
    check_answer_money(judge, answer, "custom_total", 770.00)
    # stateful: carol books the 2026-12-06 -> 2026-12-13 window for 2 adults
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 3, "stay", "759618126064467893", None, None,
        "2026-12-06", "2026-12-13", 2, 0, 0, 0, 2, 7, 110.0,
        770.0, 770.0, "confirmed", "2026-09-30")], "booking_row_shape")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
