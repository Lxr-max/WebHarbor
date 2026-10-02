#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--8.

Europe Taster guide research: the Dimos-led review posted in September 2026
(rating, travel month, operator reply), the top-rated Dimos review under the
highest-rating sort, the tour's total review count and cheapest guaranteed
departure price, then the operator's two most-reviewed other tours' most
recent reviews (author, rating, guide).

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

TASK_ID = "TourRadar--8"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_tour_page", navigated_to(traj, "/t/46923"),
                "required: /t/46923 (Europe Taster)")
    judge.check("nav_reviews_page", navigated_to(traj, "/t/46923/reviews"),
                "required: /t/46923/reviews")
    judge.check("nav_reviews_rating_sort",
                any("sort=rating" in u for u in trajectory_urls(traj)
                    if "/t/46923/reviews" in u),
                "required: the reviews sorted by highest rating")
    judge.check("nav_operator_page", navigated_to(traj, "/o/expat-explore-travel"),
                "required: the operator page")
    judge.check("nav_europe_jewel_reviews",
                navigated_to(traj, "/t/46922/reviews"),
                "required: the Europe Jewel reviews page")
    judge.check("nav_classic_europe_reviews",
                navigated_to(traj, "/t/69752/reviews"),
                "required: the Classic Europe reviews page")
    # Ground truth: the review list renders newest-first (id asc = upstream
    # display order, verified card-for-card against the live site). The only
    # Dimos-led review posted in September 2026 is Pauline's (4.3, traveled
    # August 2026, no operator reply); the top-rated Dimos-led review is
    # Sweta's 5.0.
    judge.check("answer_reviewer", contains_all(answer, ["Pauline"]),
                f"final={answer[:120]!r}")
    judge.check("answer_rating", contains_all(answer, ["4.3"]),
                "expected rating 4.3")
    judge.check("answer_traveled_month",
                contains_any(answer, ["August 2026", "traveled in august",
                                      "travelled in august"]),
                "expected traveled in August 2026")
    judge.check("answer_no_reply",
                contains_any(answer, ["no reply", "did not reply", "has not replied",
                                      "not posted a reply", "no operator reply",
                                      "without a reply", "did not post",
                                      "reply: no", "reply no"]),
                "expected: the operator did not post a reply")
    judge.check("answer_top_rated_dimos", contains_all(answer, ["Sweta"]),
                "expected Sweta as the top-rated Dimos-led review (5.0)")
    judge.check("answer_jewel_recent", contains_all(answer, ["Adebabay"]),
                "expected Adebabay as Europe Jewel's most recent reviewer")
    judge.check("answer_classic_recent", contains_all(answer, ["Chrystal"]),
                "expected Chrystal as Classic Europe's most recent reviewer")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
