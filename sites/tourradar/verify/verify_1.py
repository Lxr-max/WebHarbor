#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--1.

Kenya or Tanzania safari departing January 2027: cheapest guaranteed departure, single private room, premium insurance, guest booking. Report reference and total.

Ground truth is HARDCODED below (frozen from the reviewer's independent
DOM-asserted walkthrough + SQLite reads; never present in tasks.jsonl).
Deterministic only — no LLM calls.
Input/Output: see verify_lib.parse_args / verify_lib.run_verifier.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        trajectory_urls,
                        navigated_to_path, navigated_booking_confirmation,
                        contains_all, contains_any, contains_amount,
                        contains_int, check_trajectory_identity, check_read_only,
                        check_only_tables_changed, check_signed_in_as,
                        check_booking_row, added_bookings, booking_travelers,
                        added_rows, removed_rows, db_query, wishlist_tour_ids,
                        tour_qa_for_tour, reviews_for_tour, user_by_email)

TASK_ID = "TourRadar--1"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_kenya_serp", navigated_to(traj, "/srp/d-kenya"),
                "required: /srp/d-kenya (compare Kenya departures)")
    judge.check("nav_tanzania_serp", navigated_to(traj, "/srp/d-tanzania"),
                "required: /srp/d-tanzania (compare Tanzania departures)")
    judge.check("nav_tour_page", navigated_to(traj, "/t/4280"),
                "required: /t/4280 (Kenya Wildlife Safari)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/4280"),
                "required: /book-now/4280")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    judge.check("answer_ref", bool(re.search(r"TR-0428001\d{4}", answer)),
                f"final={answer[:120]!r}")
    judge.check("answer_total", contains_amount(answer, 2547.76),
                "expected total US$2,547.76 (single room 1725x1.36 + premium)")
    check_booking_row(judge, after_db, initial_db,
                      tour_id=4280, travelers=1, room_type="Single Room",
                      insurance="premium", schedule="deposit", total=2547.76,
                      due_today=254.78, lead_email="solo@example.com",
                      departure_date="2027-01-16")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
