#!/usr/bin/env python3
"""Deterministic verifier for TourRadar task TourRadar--13.

David: write the 5-star review on the completed tour, report how many review
entries the tour's reviews page lists after publishing, how many 5.0-rated
entries under the highest-rating sort, every tour in his Saved adventures with
the cheapest one's price, the completed booking's reference, and the tour's
next available departure.

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

TASK_ID = "TourRadar--13"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, "david.k@test.com")
    judge.check("nav_completed_booking", navigated_to(traj, "/booking/TR-000040501"),
                "required: /booking/TR-000040501 (the completed booking)")
    judge.check("nav_completed_tour", navigated_to(traj, "/t/187857"),
                "required: /t/187857 (Peru Express, the completed tour)")
    judge.check("nav_reviews_page", navigated_to(traj, "/t/187857/reviews"),
                "required: /t/187857/reviews (write + count the review entries)")
    judge.check("entered_review_body",
                "guide made every day special" in " ".join(input_texts(traj)).lower(),
                "expected the review body text in the form inputs")
    # Ground truth: 10 seeded reviews + David's = 11 listed entries; 6 of the
    # 11 are rated 5.0; his saved adventures are the 3 seeded tours (cheapest
    # 5 Day Ultimate Highland Adventure at US$504); the completed booking is
    # TR-000040501 and the tour's next available departure is October 24, 2026.
    judge.check("answer_entries_listed", contains_int(answer, 11),
                "expected 11 review entries listed after publishing")
    judge.check("answer_booking_ref", "TR-000040501" in answer,
                f"final={answer[:120]!r}")
    # DB: exactly one new review row on the completed tour
    reviews = reviews_for_tour(after_db, 187857)
    new = [r for r in reviews if r["id"] > 2105]
    judge.check("db_review_row_added", len(new) == 1,
                f"new_review_ids={[r['id'] for r in new]!r}")
    if new:
        r = new[0]
        judge.check("db_review_author", (r["author"] or "") == "David Kim",
                    f"author={r['author']!r}")
        judge.check("db_review_rating", abs((r["rating"] or 0) - 5.0) < 1e-6,
                    f"rating={r['rating']!r}")
        judge.check("db_review_title", (r["title"] or "") == "Trip of a lifetime",
                    f"title={r['title']!r}")
    check_only_tables_changed(judge, initial_db, after_db, allowed=("reviews",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
