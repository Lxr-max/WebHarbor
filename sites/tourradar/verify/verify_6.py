#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--6.

Iceland Northern Lights 5-8 days under $2,000 with instant confirmation: book 2 travelers, pay in full, first available departure.

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

TASK_ID = "TourRadar--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_iceland_listing",
                any("iceland" in u.lower()
                    for u in trajectory_urls(traj)),
                "required: an Iceland tours listing")
    judge.check("nav_tour_page", navigated_to(traj, "/t/98112"),
                "required: /t/98112 (5 Days Land of Northern Lights)")
    judge.check("nav_book_now", navigated_to(traj, "/book-now/98112"),
                "required: /book-now/98112")
    judge.check("nav_confirmation", navigated_booking_confirmation(traj),
                "required: /booking/TR-...")
    judge.check("answer_ref", bool(re.search(r"TR-9811202\d{4}", answer)),
                f"final={answer[:120]!r}")
    judge.check("answer_departure_date",
                contains_any(answer, ["October 1, 2026", "1 October 2026",
                                      "Oct 1, 2026", "October 1st, 2026"]),
                "expected departure October 1, 2026 (first available)")
    check_booking_row(judge, after_db, initial_db,
                      tour_id=98112, travelers=2, room_type="Double Room",
                      insurance="none", schedule="full", total=2712.00,
                      due_today=2712.00, lead_email="aurora@example.com",
                      departure_date="2026-10-01")
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed=("bookings", "users"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
