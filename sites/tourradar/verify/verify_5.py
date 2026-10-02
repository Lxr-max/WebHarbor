#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--5.

Machu Picchu search comparison: most-reviewed tour's 2026 sold-out share and
2-traveler deposit from its booking form (not completed), plus the cheapest and
longest results' names, prices, and available 2026 departures.

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

TASK_ID = "TourRadar--5"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_search", navigated_to(traj, "/search"),
                "required: the 'Machu Picchu' search results")
    judge.check("nav_most_reviewed_tour", navigated_to(traj, "/t/187845"),
                "required: /t/187845 (Inca Adventures - 7 Days, most reviewed)")
    judge.check("nav_booking_form", navigated_to(traj, "/book-now/187845"),
                "required: the booking form for the first available 2026 departure")
    judge.check("nav_cheapest_tour", navigated_to(traj, "/t/138437"),
                "required: /t/138437 (5 Day Cusco Travel Package, the cheapest result)")
    judge.check("answer_most_reviewed",
                contains_all(answer, ["Inca Adventures"]),
                "expected Inca Adventures as the most-reviewed result")
    judge.check("answer_review_count", contains_int(answer, 250),
                "expected 250 traveler reviews")
    judge.check("answer_soldout_share", contains_int(answer, 40),
                "expected 40% of the 60 2026 departures sold out (24 sold out)")
    judge.check("answer_deposit", contains_amount(answer, 302.40),
                "expected the 2-traveler deposit-only amount US$302.40")
    judge.check("answer_cheapest_name",
                contains_all(answer, ["5 Day Cusco Travel Package"]),
                "expected the cheapest result's name")
    judge.check("answer_cheapest_price", contains_amount(answer, 559),
                "expected the cheapest result at US$559 per person")
    judge.check("answer_cheapest_available", contains_int(answer, 30),
                "expected 30 available 2026 departures on the cheapest tour")
    judge.check("answer_longest_available", contains_int(answer, 36),
                "expected 36 available 2026 departures on the longest tour")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
