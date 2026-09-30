#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--21.

Compare three Egypt tours; book the one with rating above 4.9 and discounted price under $2,000 (2 travelers, shared room, deposit).

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

TASK_ID = "TourRadar--21"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    # the agent must have compared all three Egypt tours
    judge.check("nav_ancient_wonders", navigated_to(traj, "/t/251939"),
                "required: /t/251939 (Ancient Wonders Egypt, 14-day)")
    judge.check("nav_ultimate", navigated_to(traj, "/t/252256"),
                "required: /t/252256 (Ultimate Egyptian Experience, 10-day)")
    judge.check("nav_historic", navigated_to(traj, "/t/230867"),
                "required: /t/230867 (Historic Horizons, 8-day)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/252256"),
                "required: /book-now/252256")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    judge.check("answer_ref", bool(re.search(r"TR-25225602\d{4}", answer)),
                f"final={answer[:120]!r}")
    check_booking_row(judge, after_db, initial_db,
                      tour_id=252256, travelers=2, room_type="Double Room",
                      insurance="none", schedule="deposit", total=3800.00,
                      due_today=380.00, lead_email="value@example.com",
                      departure_date="2026-10-01")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
