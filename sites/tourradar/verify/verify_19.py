#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--19.

'Nile cruise' search: result count, the cheapest result's details (name, price,
upcoming departures, operator response rate), the most-reviewed result's
details (name, review count, rating, first available departure, 2-traveler
deposit, operator response rate), and the 'Egypt' search comparison (count,
cheapest name and price).

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

TASK_ID = "TourRadar--19"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    urls = trajectory_urls(traj)
    judge.check("nav_nile_search",
                any("nile" in u.lower() and "/search" in u for u in urls),
                "required: the 'Nile cruise' search")
    judge.check("nav_cheapest_result", navigated_to(traj, "/t/144972"),
                "required: /t/144972 (Adventure Ancient Egypt - 7 Day, the "
                "cheapest result)")
    judge.check("nav_cheapest_operator", navigated_to(traj, "/o/itaca-holiday"),
                "required: the cheapest result's operator page")
    judge.check("nav_most_reviewed", navigated_to(traj, "/t/111022"),
                "required: /t/111022 (Pharaohs Nile Cruise Adventure, the "
                "most-reviewed result)")
    judge.check("nav_most_booking_form", navigated_to(traj, "/book-now/111022"),
                "required: the most-reviewed result's booking form")
    judge.check("nav_most_operator",
                navigated_to(traj, "/o/beyond-the-nile-tours"),
                "required: the most-reviewed result's operator page")
    # Ground truth: 'Nile cruise' finds 24 tours; the cheapest is Adventure
    # Ancient Egypt - 7 Day at US$560 (upcoming departures listed, Itaca
    # Holiday response rate 100%); the most-reviewed is the Pharaohs Nile
    # Cruise Adventure (1,652 reviews, 4.7, first available October 1, 2026,
    # 2-traveler deposit US$195.00, Beyond The Nile Tours response rate 96%);
    # 'Egypt' finds 13 tours with the same cheapest tour.
    judge.check("answer_cheapest_name",
                contains_all(answer, ["Adventure Ancient Egypt"]),
                "expected Adventure Ancient Egypt - 7 Day as the cheapest result")
    judge.check("answer_cheapest_price", contains_amount(answer, 560),
                "expected the cheapest result at US$560")
    judge.check("answer_cheapest_upcoming",
                contains_any(answer, ["upcoming departures", "lists departures",
                                       "has departures", "upcoming departure",
                                       "departures listed"]),
                "expected the cheapest result to list upcoming departures")
    judge.check("answer_cheapest_rr", contains_int(answer, 100),
                "expected the cheapest operator's 100% response rate")
    judge.check("answer_most_name",
                contains_all(answer, ["Pharaohs Nile Cruise"]),
                "expected the Pharaohs Nile Cruise Adventure as most-reviewed")
    judge.check("answer_most_reviews", contains_int(answer, 1652),
                "expected 1,652 reviews on the most-reviewed result")
    judge.check("answer_most_departure",
                contains_any(answer, ["October 1, 2026", "1 October 2026",
                                      "Oct 1, 2026"]),
                "expected the most-reviewed result's first available departure "
                "October 1, 2026")
    judge.check("answer_most_deposit", contains_amount(answer, 195.00),
                "expected the most-reviewed result's 2-traveler deposit US$195.00")
    judge.check("answer_most_rr", contains_int(answer, 96),
                "expected the most-reviewed operator's 96% response rate")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
