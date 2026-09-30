#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--4.

Toyota dealers rated 4+ within 100 miles sorted by highest ratings: match
count + top dealer; its Monday hours + new-cars phone; the three most recent
reviews; then log in as dana.k@test.com, search used Toyota RAV4s within 50
miles and save the search as 'RAV4 watch' with weekly alerts. Stateful
(dana +1 saved search)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_all, contains_any,
                        check_trajectory_identity, check_signed_in_as,
                        check_saved_search, check_only_tables_changed)

TASK_ID = "Cars.com--4"
DEALER_PATH = "/dealers/5382245/marysville-toyota/"
DANA = "dana.k@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, DANA)

    judge.check("nav_dealers_directory", navigated_to(traj, "/dealers/"),
                "required: the dealer directory")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_dealer_reviews", navigated_to(traj, DEALER_PATH + "reviews/"),
                "required: the dealer's reviews page")
    judge.check("nav_srp_rav4", navigated_to(traj, "/shopping/results/"),
                "required: the used-RAV4 SERP")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # directory: 1 match; Marysville Toyota 4.9 (1,086 reviews), 38 miles
    judge.check("answer_matches", contains_int(answer, 1),
                "expected 1 matching dealer")
    judge.check("answer_top_dealer", contains_all(answer, ["Marysville Toyota"]),
                "expected Marysville Toyota as the top dealer")
    judge.check("answer_rating_reviews",
                contains_any(answer, ["4.9"]) and contains_any(answer, ["1,086", "1086"]),
                "expected rating 4.9 with 1,086 reviews")
    judge.check("answer_distance", contains_int(answer, 38),
                "expected 38 miles away")

    # dealer page: Monday 9:00am-7:00pm; new-cars phone (360) 474-4089
    judge.check("answer_monday_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["7:00"]),
                "expected Monday 9:00am-7:00pm")
    judge.check("answer_new_phone", contains_any(answer, ["474-4089"]),
                "expected the new-cars phone (360) 474-4089")

    # three most recent reviews: Michael Nuno 5.0 2026-05-19,
    # Robert Moya 5.0 2026-05-17, Clyde Libolt 4.0 2026-05-16
    judge.check("answer_recent_reviews",
                contains_all(answer, ["Michael Nuno", "Robert Moya", "Clyde Libolt"]),
                "expected the three most recent review authors")
    judge.check("answer_recent_review_details",
                contains_all(answer, ["2026-05-19", "2026-05-17", "2026-05-16"]),
                "expected the three review dates")

    # garage: the saved search 'RAV4 watch' with weekly alerts
    judge.check("answer_garage_search",
                contains_all(answer, ["RAV4 watch", "weekly"]),
                "expected the saved search 'RAV4 watch' with weekly alerts")

    # DB: dana now has 3 saved searches (2 seed + RAV4 watch weekly)
    check_saved_search(judge, after_db, DANA, "RAV4 watch", "weekly")
    rows = __import__("verify_lib").saved_searches_for(after_db, DANA)
    judge.check("dana_search_count", len(rows) == 3,
                f"saved_searches={[r['name'] for r in rows]!r}")
    check_only_tables_changed(judge, initial_db, after_db, ("saved_searches",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
