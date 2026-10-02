#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--15.

Morocco >110-review tours with the smallest maximum group size: compare the
candidates on their tour pages, then the two finalists' booking forms
(2-traveler per-person price and deposit-only amount), plus the total Morocco
tour count and how many have more than 110 reviews.

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

TASK_ID = "TourRadar--15"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_morocco_serp", navigated_to(traj, "/srp/d-morocco"),
                "required: the Morocco tours page")
    judge.check("nav_candidate_timeless", navigated_to(traj, "/t/45549"),
                "required: /t/45549 (Timeless Morocco candidate)")
    judge.check("nav_candidate_sahara", navigated_to(traj, "/t/150261"),
                "required: /t/150261 (5 day trip: Sahara Fun Outdoor Experience)")
    judge.check("nav_candidate_casablanca", navigated_to(traj, "/t/142026"),
                "required: /t/142026 (Morocco 7 Days Tour From Casablanca)")
    judge.check("nav_booking_form_casablanca",
                navigated_to(traj, "/book-now/142026"),
                "required: the Casablanca finalist's booking form")
    judge.check("nav_booking_form_sahara",
                navigated_to(traj, "/book-now/150261"),
                "required: the Sahara Fun finalist's booking form")
    # Ground truth: 7 Morocco tours, 3 with >110 reviews (Timeless Morocco
    # 2-15, Sahara Fun 1-10, Morocco 7 Days From Casablanca 1-6); the winner
    # is Morocco 7 Days Tour From Casablanca (max group size 6).
    judge.check("answer_morocco_total", contains_int(answer, 7),
                "expected 7 Morocco tours in total")
    judge.check("answer_over_110", contains_int(answer, 3),
                "expected 3 Morocco tours with more than 110 reviews")
    judge.check("answer_winner",
                contains_all(answer, ["Morocco 7 Days Tour From Casablanca"]),
                "expected Morocco 7 Days Tour From Casablanca as the winner")
    judge.check("answer_winner_group_size",
                contains_any(answer, ["1-6", "1 – 6", "1 to 6", "max 6",
                                      "maximum group size 6"]),
                "expected the winner's group size range 1-6")
    judge.check("answer_winner_price", contains_amount(answer, 1322),
                "expected the winner at US$1,322 per person")
    judge.check("answer_runnerup",
                contains_all(answer, ["Sahara Fun"]),
                "expected the 5 day trip: Sahara Fun Outdoor Experience as runner-up")
    judge.check("answer_runnerup_group_size",
                contains_any(answer, ["1-10", "1 – 10", "1 to 10", "max 10",
                                      "maximum group size 10"]),
                "expected the runner-up's group size range 1-10")
    judge.check("answer_deposit_casablanca", contains_amount(answer, 264.40),
                "expected the Casablanca form's 2-traveler deposit US$264.40")
    judge.check("answer_deposit_sahara", contains_amount(answer, 230.60),
                "expected the Sahara Fun form's 2-traveler deposit US$230.60")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
