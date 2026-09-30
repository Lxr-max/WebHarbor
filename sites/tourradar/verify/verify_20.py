#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--20.

Three operators (Expat Explore Travel, Intrepid Travel, Trafalgar): overall
rating, response time, response rate, listed-tour count, and each operator's
most-reviewed tour (opened from the operator page), then the fastest
responder, highest response rate, and most-listed tours.

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

TASK_ID = "TourRadar--20"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_expat_operator", navigated_to(traj, "/o/expat-explore-travel"),
                "required: the Expat Explore Travel operator page")
    judge.check("nav_intrepid_operator", navigated_to(traj, "/o/intrepid-travel"),
                "required: the Intrepid Travel operator page")
    judge.check("nav_trafalgar_operator", navigated_to(traj, "/o/trafalgar"),
                "required: the Trafalgar operator page")
    judge.check("nav_expat_top_tour", navigated_to(traj, "/t/46922"),
                "required: /t/46922 (Europe Jewel, Expat's most-reviewed tour)")
    judge.check("nav_intrepid_top_tour", navigated_to(traj, "/t/5092"),
                "required: /t/5092 (Mexico Unplugged, Intrepid's most-reviewed tour)")
    judge.check("nav_trafalgar_top_tour", navigated_to(traj, "/t/82244"),
                "required: /t/82244 (Canada's Rockies, Trafalgar's most-reviewed tour)")
    # Ground truth (seed DB + live pages): Expat Explore 4.5 / 10 hours /
    # 84% / 4 tours / Europe Jewel (406 reviews); Intrepid 4.5 / 3 hours /
    # 80% / 9 tours / Mexico Unplugged (126 reviews); Trafalgar 4.5 /
    # 9 hours / 72% / 3 tours / Canada's Rockies (169 reviews). Fastest:
    # Intrepid (3 hours); highest response rate: Expat (84%); most tours:
    # Intrepid (9).
    judge.check("answer_expat_rating", contains_all(answer, ["4.5"]),
                "expected Expat Explore rating 4.5")
    judge.check("answer_expat_time",
                contains_any(answer, ["10 hours", "10h", "within 10 hours"]),
                "expected Expat response time 10 hours")
    judge.check("answer_expat_rate", contains_int(answer, 84),
                "expected Expat response rate 84%")
    judge.check("answer_expat_tours", contains_int(answer, 4),
                "expected Expat to list 4 tours")
    judge.check("answer_expat_top",
                contains_all(answer, ["Europe Jewel"]) and contains_int(answer, 406),
                "expected Europe Jewel (406 reviews) as Expat's most-reviewed tour")
    judge.check("answer_intrepid_time",
                contains_any(answer, ["3 hours", "3h", "within 3 hours"]),
                "expected Intrepid response time 3 hours")
    judge.check("answer_intrepid_rate", contains_int(answer, 80),
                "expected Intrepid response rate 80%")
    judge.check("answer_intrepid_tours", contains_int(answer, 9),
                "expected Intrepid to list 9 tours")
    judge.check("answer_intrepid_top",
                contains_all(answer, ["Mexico Unplugged"]) and contains_int(answer, 126),
                "expected Mexico Unplugged (126 reviews) as Intrepid's most-reviewed tour")
    judge.check("answer_trafalgar_time",
                contains_any(answer, ["9 hours", "9h", "within 9 hours"]),
                "expected Trafalgar response time 9 hours")
    judge.check("answer_trafalgar_rate", contains_int(answer, 72),
                "expected Trafalgar response rate 72%")
    judge.check("answer_trafalgar_tours", contains_int(answer, 3),
                "expected Trafalgar to list 3 tours")
    judge.check("answer_trafalgar_top",
                contains_any(answer, ["Canada's Rockies", "Canadas Rockies",
                                      "Canada’s Rockies"]) and contains_int(answer, 169),
                "expected Canada's Rockies (169 reviews) as Trafalgar's "
                "most-reviewed tour")
    judge.check("answer_fastest",
                contains_any(answer, ["intrepid is the fastest",
                                       "fastest is intrepid",
                                       "fastest: intrepid",
                                       "intrepid responds fastest",
                                       "intrepid travel responds fastest",
                                       "fastest responder is intrepid"]),
                "expected Intrepid Travel named the fastest responder")
    judge.check("answer_highest_rate",
                contains_any(answer, ["expat explore travel has the highest response rate",
                                       "highest response rate is expat",
                                       "highest response rate: expat",
                                       "expat has the highest response rate",
                                       "expat explore has the highest response rate"]),
                "expected Expat Explore Travel named the highest response rate")
    judge.check("answer_most_tours",
                contains_any(answer, ["intrepid travel lists the most tours",
                                       "most tours is intrepid",
                                       "most tours: intrepid",
                                       "intrepid lists the most tours",
                                       "operator with the most tours is intrepid"]),
                "expected Intrepid Travel named the operator with the most tours")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
