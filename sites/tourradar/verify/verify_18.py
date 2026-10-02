#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--18.

Greek island-hopping under US$1,800 per person with a private room: the
best-reviewed candidate's details (rating, next guaranteed departure, price
basis, first reviewer), its booking form (per-person, Single Room, 2-traveler
deposit), compared with the other island-hopping tour within budget (name,
rating, price, next guaranteed departure, deposit). No booking completed.

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

TASK_ID = "TourRadar--18"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_best_tour", navigated_to(traj, "/t/154254"),
                "required: /t/154254 (Cultural Athens & Island Hopping "
                "Mykonos - Santorini, the best-reviewed within budget)")
    judge.check("nav_best_booking_form", navigated_to(traj, "/book-now/154254"),
                "required: the best candidate's booking form")
    judge.check("nav_best_reviews", navigated_to(traj, "/t/154254/reviews"),
                "required: the best candidate's reviews page (first reviewer)")
    judge.check("nav_other_tour", navigated_to(traj, "/t/158180"),
                "required: /t/158180 (Best of Greece (15 days) Athens & 4 "
                "Islands, the other island-hopping tour within budget)")
    judge.check("nav_other_booking_form", navigated_to(traj, "/book-now/158180"),
                "required: the other candidate's booking form")
    # Ground truth: within the US$1,800 budget the two island-hopping tours
    # are Cultural Athens & Island Hopping Mykonos - Santorini (4.6, 106
    # reviews) and Best of Greece 4 Islands (4.5, 73 reviews); the
    # best-reviewed is the former. Its next guaranteed departure is
    # September 30, 2026, price based on Private Double Room, first reviewer
    # Linda; the form shows per-person US$1,249, Single Room US$1,699, deposit
    # US$249.80 for 2 travelers. The other tour's next guaranteed departure is
    # September 30, 2026 with a US$374.20 deposit.
    judge.check("answer_best_name",
                contains_all(answer, ["Cultural Athens"]),
                "expected Cultural Athens & Island Hopping as the best-reviewed")
    judge.check("answer_best_rating", contains_all(answer, ["4.6"]),
                "expected the best candidate's rating 4.6")
    judge.check("answer_best_departure",
                contains_any(answer, ["September 30, 2026", "30 September 2026",
                                      "Sep 30, 2026"]),
                "expected the next guaranteed departure September 30, 2026")
    judge.check("answer_price_basis",
                contains_any(answer, ["private double room", "private room",
                                      "double room"]),
                "expected the price basis Private Double Room")
    judge.check("answer_first_reviewer", contains_all(answer, ["Linda"]),
                "expected Linda as the first reviewer on the reviews page")
    judge.check("answer_form_per_person", contains_amount(answer, 1249),
                "expected the form's per-person price US$1,249")
    judge.check("answer_single_room", contains_amount(answer, 1699),
                "expected the Single Room price US$1,699")
    judge.check("answer_best_deposit", contains_amount(answer, 249.80),
                "expected the best candidate's 2-traveler deposit US$249.80")
    judge.check("answer_other_name",
                contains_all(answer, ["Best of Greece"]),
                "expected Best of Greece (15 days) Athens & 4 Islands as the other tour")
    judge.check("answer_other_rating", contains_all(answer, ["4.5"]),
                "expected the other candidate's rating 4.5")
    judge.check("answer_other_price", contains_amount(answer, 1871),
                "expected the other candidate at US$1,871")
    judge.check("answer_other_deposit", contains_amount(answer, 374.20),
                "expected the other candidate's 2-traveler deposit US$374.20")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
