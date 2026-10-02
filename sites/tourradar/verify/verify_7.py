#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--7.

Europe Taster group-of-3 booking options (NOT completed): per-person price,
both insurance prices, deposit-only amount, cheaper insurance, Single Room
price, 2-traveler Premium price, second-cheapest guaranteed departure, and the
operator's Europe Jewel comparison.

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

TASK_ID = "TourRadar--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_tour_page", navigated_to(traj, "/t/46923"),
                "required: /t/46923 (Europe Taster)")
    judge.check("nav_booking_form", navigated_to(traj, "/book-now/46923"),
                "required: the booking form on the cheapest guaranteed departure")
    judge.check("answer_per_person", contains_amount(answer, 1635),
                "expected the shared-room per-person price US$1,635")
    judge.check("answer_premium", contains_amount(answer, 421.83),
                "expected Premium Protection US$421.83 for 3 travelers")
    judge.check("answer_cancellation", contains_amount(answer, 237.89),
                "expected Trip Cancellation Only US$237.89 for 3 travelers")
    judge.check("answer_deposit", contains_amount(answer, 490.50),
                "expected the deposit-only amount US$490.50 today")
    judge.check("answer_cheaper_insurance",
                contains_any(answer, ["cancellation is cheaper",
                                       "cheaper insurance is trip cancellation",
                                       "trip cancellation only is cheaper",
                                       "cancellation insurance is cheaper"]),
                "expected Trip Cancellation Only to be named the cheaper insurance")
    judge.check("answer_single_room", contains_amount(answer, 2224),
                "expected the Single Room per-person price US$2,224")
    judge.check("answer_premium_2travelers", contains_amount(answer, 281.22),
                "expected Premium Protection US$281.22 for 2 travelers")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
