#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--4.

Nepal operator comparison: SERP operator filter counts and cheapest tours for
Nepal Hiking Team vs Nepal Social Treks, both operator pages (ratings, response
times), then the cheaper operator's tour: first guaranteed October 2026
departure and the 2-traveler deposit-only amount from its booking form.

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

TASK_ID = "TourRadar--4"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_nepal_serp", navigated_to(traj, "/srp/d-nepal"),
                "required: the Nepal tours page (SERP) with the operator filter")
    judge.check("nav_nepal_serp_filtered",
                any("operator=" in u for u in trajectory_urls(traj)
                    if "/srp/d-nepal" in u),
                "required: the operator filter applied on the Nepal SERP")
    judge.check("nav_nht_operator", navigated_to(traj, "/o/nepal-hiking-team"),
                "required: the Nepal Hiking Team operator page")
    judge.check("nav_nst_operator", navigated_to(traj, "/o/nepal-social-treks"),
                "required: the Nepal Social Treks operator page")
    judge.check("nav_cheaper_tour", navigated_to(traj, "/t/114044"),
                "required: /t/114044 (Explore Nepal Tours 11 Days, the cheaper "
                "operator's tour)")
    judge.check("nav_booking_form", navigated_to(traj, "/book-now/114044"),
                "required: the booking form for the first guaranteed Oct-2026 departure")
    judge.check("answer_nht_rating", contains_all(answer, ["4.9"]),
                "expected Nepal Hiking Team rating 4.9")
    judge.check("answer_nst_rating", contains_all(answer, ["4.8"]),
                "expected Nepal Social Treks rating 4.8")
    judge.check("answer_nht_response",
                contains_any(answer, ["9 hours", "9h", "within 9 hours"]),
                "expected Nepal Hiking Team response time 9 hours")
    judge.check("answer_nst_response",
                contains_any(answer, ["5 hours", "5h", "within 5 hours"]),
                "expected Nepal Social Treks response time 5 hours")
    judge.check("answer_nht_price", contains_amount(answer, 1475),
                "expected Nepal Hiking Team's cheapest Nepal tour at US$1,475")
    judge.check("answer_nst_price", contains_amount(answer, 890),
                "expected Nepal Social Treks' cheapest Nepal tour at US$890")
    judge.check("answer_oct_departure",
                contains_any(answer, ["October 1, 2026", "1 October 2026",
                                      "Oct 1, 2026"]),
                "expected the first guaranteed October 2026 departure: October 1, 2026")
    judge.check("answer_dep_price", contains_amount(answer, 890),
                "expected the departure price US$890")
    judge.check("answer_deposit_2travelers", contains_amount(answer, 178.00),
                "expected the 2-traveler deposit-only amount US$178.00")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
