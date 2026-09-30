#!/usr/bin/env python3
"""Deterministic verifier for Airbnb--14 (airbnb).

Ground truth below is HARDCODED (re-frozen for the r2/r3 fix rounds and
independently re-verified by the reviewer: real Playwright walks on the
reviewer's own image builds — r2: wh-airbnb-r2review @ 46116 from
d23640b0; r3: wh-airbnb-r3review @ 49116 from fed30bf9 — seed sha256
recorded in verify_lib.py) — never read from tasks.jsonl.

R2 RE-FREEZE NOTES (contribution fix round, review findings B3/B4 +
question re-anchor): (a) the Experiences search now renders a destination
selector, so New York experiences are UI-reachable; (b) the experience PDP
now renders the captured things_to_know / guest_requirements payloads as
structured text (the old build iterated the JSON strings, leaking Python
reprs), so the activity-level line reads "The activity level for this
experience is moderate."; (c) the unanswerable "first guest review's
reviewer and month" ask (the capture carries no reviewer/date for
experience reviews) was replaced by "the minimum guest age from its guest
requirements" (12 for this experience).

Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Airbnb--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    # navigation: NYC experiences SERP in the Cultural tours category, the
    # first detail, the second, login, the book flow.
    check_visited_path(judge, traj, "nav_exp_serp",
                       r"/s/experiences\?[^ ]*city=new-york")
    check_visited_path(judge, traj, "nav_category",
                       r"/s/experiences\?[^ ]*category=Cultural\+tours")
    check_visited_path(judge, traj, "nav_first", r"/experiences/371834")
    check_visited_path(judge, traj, "nav_second", r"/experiences/445486")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_book", r"/experiences/371834/book")
    # answer ground truth
    check_answer_phrase(judge, answer, "first_name",
                        "Hamilton & Washington\u2019s New York with a historian")
    check_answer_money(judge, answer, "first_price", 48)
    check_answer_number(judge, answer, "first_rating_count", 135)
    check_answer_number(judge, answer, "min_age", 12)
    check_answer_any(judge, answer, "activity_level", ["moderate"])
    check_answer_phrase(judge, answer, "second_name",
                        "Discover Hasidic Brooklyn with a local Rabbi")
    check_answer_money(judge, answer, "second_price", 69)
    added = new_bookings(judge, initial, after)
    check_answer_has_new_booking_code(judge, answer, after, added, "booking_code")
    check_answer_money(judge, answer, "booking_total", 144.00)
    # stateful: bob books the first Cultural tour for 3 guests on the first date
    check_rows_added(judge, initial, after, "bookings", [(
        None, "rx:^HM[A-Z0-9]{8}$", 2, "experience", None, "371834",
        "2026-10-10T12:00:00-04:00", None, None, 3, 0, 0, 0, 3,
        None, None, 144.0, 144.0, "confirmed", "2026-09-30")],
        "booking_row_shape")
    check_only_tables_changed(judge, initial, after, {"bookings"})



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
