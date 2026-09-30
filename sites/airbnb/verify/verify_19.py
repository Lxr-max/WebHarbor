#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--19 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.


R2 RE-FREEZE NOTE (contribution fix round, review finding B3): the
Experiences search now renders a destination selector, so Miami
experiences are UI-reachable; the intended truth is unchanged.

Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: Miami experiences SERP in the Water sports category, the
    # price_asc sort, the cheapest detail, the second cheapest, login, book.
    check_visited_path(judge, traj, "nav_exp_serp", r"/s/experiences\?[^ ]*city=miami")
    check_visited_path(judge, traj, "nav_category", r"/s/experiences\?[^ ]*category=Water\+sports")
    check_visited_path(judge, traj, "nav_sorted", r"/s/experiences\?[^ ]*sort=price_asc")
    check_visited_path(judge, traj, "nav_cheap", r"/experiences/4601632")
    check_visited_path(judge, traj, "nav_second", r"/experiences/704294")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_book", r"/experiences/4601632/book")
    # answer ground truth
    check_answer_number(judge, answer, "ws_count", 6)
    check_answer_phrase(judge, answer, "cheapest_name",
                        "Biscayne Bay jet ski adventure in Miami")
    check_answer_money(judge, answer, "cheapest_price", 50)
    check_answer_number(judge, answer, "cheapest_rating", "4.51")
    check_answer_phrase(judge, answer, "second_name",
                        "Walk Raccoon Island and Swim the Bay")
    check_answer_money(judge, answer, "second_price", 70)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_money(judge, answer, "booking_total", 200.00)
    check_answer_number(judge, answer, "alice_trips_after", 3)
    # stateful: alice books the cheapest for 4 guests on the first date
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 1, "experience", None, "4601632",
        "2026-09-29T22:00:00-04:00", None, None, 4, 0, 0, 0, 4,
        None, None, 200.0, 200.0, "confirmed", "2026-09-30")],
        "booking_row_shape")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
