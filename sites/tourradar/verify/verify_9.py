#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--9.

Kenya safari research: highest-rated Kenya tour with the traveler-review
tie-break (two tours tied at 5.0; the one with more reviews wins), its Good to
Know vaccinations and visa advice, cheapest departure price and date, the
booking form's Single Room price, the other top-rated tour's data (review
count, cheapest departure, Typhoid), and the most-reviewed Kenya tour.

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

TASK_ID = "TourRadar--9"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_kenya_tours", navigated_to(traj, "/srp/d-kenya"),
                "required: the Kenya tours page")
    judge.check("nav_winner_tour", navigated_to(traj, "/t/162795"),
                "required: /t/162795 (5 Days Amboseli, Tsavo West & Tsavo East "
                "Coastal Safari — the tie-break winner with 17 reviews)")
    judge.check("nav_booking_form", navigated_to(traj, "/book-now/162795"),
                "required: the winner's booking form (Single Room price)")
    judge.check("nav_other_top_tour", navigated_to(traj, "/t/312271"),
                "required: /t/312271 (the other 5.0-rated Kenya tour)")
    # Ground truth: two Kenya tours tie at 5.0 — Amboseli (17 reviews) and
    # Masai Mara (16 reviews); the tie-break ("more traveler reviews") makes
    # the Amboseli safari the unique answer.
    judge.check("answer_winner",
                contains_all(answer, ["Amboseli"]),
                "expected the 5 Days Amboseli, Tsavo West & Tsavo East Coastal Safari")
    judge.check("answer_rating", contains_all(answer, ["5.0", "5"]),
                "expected the tour rating 5.0")
    judge.check("answer_review_count", contains_int(answer, 17),
                "expected 17 traveler reviews")
    judge.check("answer_vaccinations",
                contains_all(answer, ["Typhoid"]) and
                contains_any(answer, ["Hepatitis A", "Hep A"]),
                "expected Typhoid and Hepatitis A among the recommended vaccinations")
    judge.check("answer_visa",
                contains_any(answer, ["visa"]),
                "expected visa advice from Good to Know")
    judge.check("answer_dep_date",
                contains_any(answer, ["September 30, 2026", "30 September 2026",
                                      "Sep 30, 2026"]),
                "expected the cheapest departure September 30, 2026")
    judge.check("answer_dep_price", contains_amount(answer, 2261),
                "expected the cheapest departure at US$2,261")
    judge.check("answer_single_room", contains_amount(answer, 3075),
                "expected the Single Room price US$3,075")
    judge.check("answer_other_reviews", contains_int(answer, 16),
                "expected the other top-rated tour's 16 reviews")
    judge.check("answer_other_price", contains_amount(answer, 1438),
                "expected the other top-rated tour's cheapest departure US$1,438")
    judge.check("answer_other_typhoid",
                contains_any(answer, ["typhoid"]),
                "expected the other tour's Good to Know to list Typhoid")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
