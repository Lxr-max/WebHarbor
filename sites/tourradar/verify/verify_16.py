#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--16.

Peru Medium-intensity tours: the longest one's name, duration, start/end
cities (read from its booking form, not completed) and cheapest available
departure, compared with the cheapest Medium-intensity tour; plus the total
Medium-intensity count.

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

TASK_ID = "TourRadar--16"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_peru_serp", navigated_to(traj, "/srp/d-peru"),
                "required: the Peru tours page")
    judge.check("nav_medium_filter",
                any("physical=" in u for u in trajectory_urls(traj)
                    if "/srp/d-peru" in u),
                "required: the Medium intensity filter applied")
    judge.check("nav_longest_tour", navigated_to(traj, "/t/76964"),
                "required: /t/76964 (Cusco & Salkantay Trekking to Machu "
                "Picchu, the longest Medium tour)")
    judge.check("nav_longest_booking_form", navigated_to(traj, "/book-now/76964"),
                "required: the longest tour's booking form (to see the cities)")
    judge.check("nav_cheapest_tour", navigated_to(traj, "/t/138441"),
                "required: /t/138441 (7 Day Cusco Travel Package, the cheapest "
                "Medium tour)")
    # Ground truth: 6 Medium-intensity Peru tours; the longest is the 8-day
    # Cusco & Salkantay Trekking to Machu Picchu (starts and ends in Cusco);
    # its cheapest available departure is November 1, 2026 at US$1,048; the
    # cheapest Medium tour is the 7 Day Cusco Travel Package at US$669 with
    # its cheapest departure October 30, 2026.
    judge.check("answer_medium_count", contains_int(answer, 6),
                "expected 6 Medium-intensity Peru tours")
    judge.check("answer_longest",
                contains_all(answer, ["Cusco & Salkantay"]),
                "expected Cusco & Salkantay Trekking to Machu Picchu as the longest")
    judge.check("answer_longest_duration", contains_int(answer, 8),
                "expected the longest tour's 8-day duration")
    judge.check("answer_start_city", contains_all(answer, ["Cusco"]),
                "expected the start city Cusco")
    judge.check("answer_end_city",
                answer.lower().count("cusco") >= 2,
                "expected the end city Cusco (both cities are Cusco)")
    judge.check("answer_longest_dep_date",
                contains_any(answer, ["November 1, 2026", "1 November 2026",
                                      "Nov 1, 2026"]),
                "expected the longest tour's cheapest available departure "
                "November 1, 2026")
    judge.check("answer_longest_dep_price", contains_amount(answer, 1048),
                "expected the longest tour's cheapest available departure at US$1,048")
    judge.check("answer_cheapest_name",
                contains_all(answer, ["7 Day Cusco Travel Package"]),
                "expected the 7 Day Cusco Travel Package as the cheapest Medium tour")
    judge.check("answer_cheapest_price", contains_amount(answer, 669),
                "expected the cheapest Medium tour at US$669")
    judge.check("answer_cheapest_dep_date",
                contains_any(answer, ["October 30, 2026", "30 October 2026",
                                      "Oct 30, 2026"]),
                "expected the cheapest Medium tour's departure October 30, 2026")
    judge.check("answer_which_cheaper",
                contains_any(answer, ["7 day cusco travel package is cheaper",
                                       "cheaper tour is the 7 day cusco travel package",
                                       "the cheaper tour is the 7 day cusco",
                                       "cheaper tour is 7 day cusco",
                                       "cheaper of the two tours is the 7 day cusco"]),
                "expected the 7 Day Cusco Travel Package named the cheaper one")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
