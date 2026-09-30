#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--10.

Inca Adventures (7-day Lima to Machu Picchu) Day 5 research + full reviews
page + cheapest available departure, compared with the 4-Day Classic Inca
Trail (Small Group & Vistadome Train): Day 1/Day 4 titles, rating, listed
reviews, first available departure.

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

TASK_ID = "TourRadar--10"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_inca_adventures", navigated_to(traj, "/t/187845"),
                "required: /t/187845 (Inca Adventures - 7 Days)")
    judge.check("nav_inca_reviews", navigated_to(traj, "/t/187845/reviews"),
                "required: the Inca Adventures full reviews page")
    judge.check("nav_classic_inca_trail", navigated_to(traj, "/t/133014"),
                "required: /t/133014 (4-Day Classic Inca Trail - Small Group "
                "& Vistadome Train)")
    judge.check("answer_day5_title",
                contains_all(answer, ["Machu Picchu"]),
                "expected Day 5 titled Machu Picchu")
    judge.check("answer_day5_content",
                contains_any(answer, ["shuttle bus", "guided tour",
                                      "Huayna Picchu"]),
                "expected Day 5's shuttle bus / guided tour / Huayna Picchu hike")
    judge.check("answer_optional_days", contains_int(answer, 4),
                "expected 4 days listing optional activities")
    judge.check("answer_reviews_listed", contains_int(answer, 10),
                "expected 10 review entries listed on the reviews page")
    judge.check("answer_cheapest_available_date",
                contains_any(answer, ["November 7, 2026", "7 November 2026",
                                      "Nov 7, 2026"]),
                "expected the cheapest available departure November 7, 2026")
    judge.check("answer_cheapest_available_price", contains_amount(answer, 1323),
                "expected the cheapest available departure at US$1,323")
    judge.check("answer_cit_day1",
                contains_all(answer, ["Cusco to Km 82"]),
                "expected the Classic Inca Trail Day 1 'Cusco to Km 82 - "
                "Patallacta - Ayapata'")
    judge.check("answer_cit_day4",
                contains_all(answer, ["Sun Gate"]),
                "expected the Classic Inca Trail Day 4 'Wiñay Wayna to Sun "
                "Gate - Machu Picchu - Cusco'")
    judge.check("answer_cit_rating", contains_all(answer, ["5.0", "5"]),
                "expected the Classic Inca Trail rating 5.0")
    judge.check("answer_cit_reviews_listed", contains_int(answer, 12),
                "expected 12 review entries listed on the Classic Inca Trail page")
    judge.check("answer_cit_first_available",
                contains_any(answer, ["October 18, 2026", "18 October 2026",
                                      "Oct 18, 2026"]),
                "expected the Classic Inca Trail first available departure "
                "October 18, 2026")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
