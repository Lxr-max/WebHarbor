#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--12.

Ask the Ultimate Egyptian Experience operator a question (Curious Traveler),
report the confirmation, then research Egypt tours: the cheapest (rating,
upcoming departures), the most-reviewed (name, review count, price, first
available departure), and the total Egypt tour count.

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
                        trajectory_urls, input_texts,
                        navigated_to_path, navigated_booking_confirmation,
                        contains_all, contains_any, contains_amount,
                        contains_int, check_trajectory_identity, check_read_only,
                        check_only_tables_changed, check_signed_in_as,
                        check_booking_row, added_bookings, booking_travelers,
                        added_rows, removed_rows, db_query, wishlist_tour_ids,
                        tour_qa_for_tour, reviews_for_tour, user_by_email)

TASK_ID = "TourRadar--12"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_ultimate_tour", navigated_to(traj, "/t/252256"),
                "required: /t/252256 (Ultimate Egyptian Experience)")
    judge.check("entered_question",
                "airport pickup" in " ".join(input_texts(traj)).lower(),
                "expected the airport-pickup question in the ask form inputs")
    judge.check("answer_confirmation",
                contains_any(answer, ["sent to the operator", "has been sent",
                                      "question was submitted",
                                      "thank you"]),
                "expected the on-site confirmation message")
    judge.check("confirmation_not_negated", not re.search(r"\b(?:not|never|failed|unsent)\b", answer, re.I), "submission must be confirmed")
    # DB: exactly one new Q&A row on the Ultimate Egyptian Experience tour
    qa = tour_qa_for_tour(after_db, 252256)
    new_qa = [q for q in qa if q["id"] > 819]
    judge.check("db_qa_row_added", len(new_qa) == 1,
                f"new_qa_rows={[q['id'] for q in new_qa]!r}")
    if new_qa:
        q = new_qa[0]
        judge.check("db_qa_question",
                    "airport pickup" in (q["question"] or "").lower(),
                    f"question={q['question']!r}")
        judge.check("db_qa_asker", (q["asker"] or "") == "Curious Traveler",
                    f"asker={q['asker']!r}")
    check_only_tables_changed(judge, initial_db, after_db, allowed=("tour_qa",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
