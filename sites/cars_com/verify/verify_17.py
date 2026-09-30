#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--17.

Log in as alice.j@test.com; open the 2025 Honda Civic research page (starting
price, trim count, cheapest trim's price/MPG/seat capacity, consumer rating +
recommendation %, two good + two bad points); open its listings section,
narrow to under $30,000, save the search as 'Civic research' with daily
alerts; open any comparison that includes the Honda Accord and report both
cars' starting MSRPs. Stateful (alice +1 saved search).

DATA NOTE: the 2025 Civic trim table carries model-year rows ('2023'/'2025'/
'2026') in the trim-name column (frozen upstream capture); the cheapest trim
row is the one shown as '2023' at $21,700 (32/41 MPG, 5 seats). The verifier
pins the price/MPG/seats and leaves the row label to the judge rubric."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_search,
                        check_only_tables_changed)

TASK_ID = "Cars.com--17"
CIVIC_PAGE = "/research/honda-civic-2025/"
COMPARE_PATH = "/research/compare/honda-accord-vs-toyota-camry/"
ALICE = "alice.j@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, ALICE)

    judge.check("nav_civic_research", navigated_to(traj, CIVIC_PAGE),
                f"required: {CIVIC_PAGE}")
    judge.check("nav_civic_listings", navigated_to(traj, "/shopping/results/"),
                "required: the Civic listings SERP")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")
    judge.check("nav_accord_compare", navigated_to(traj, COMPARE_PATH),
                f"required: {COMPARE_PATH}")

    # research page: starting price $24,250; 9 trims listed
    judge.check("answer_starting_price", contains_price(answer, 24250),
                "expected the starting price $24,250")
    judge.check("answer_trim_count", contains_int(answer, 9),
                "expected 9 trims listed")

    # cheapest trim row: $21,700 at 32 city / 41 highway MPG, 5 seats
    judge.check("answer_cheapest_trim_price", contains_price(answer, 21700),
                "expected the cheapest trim at $21,700")
    judge.check("answer_cheapest_trim_mpg_seats",
                contains_all(answer, ["32"]) and contains_all(answer, ["41"])
                and contains_int(answer, 5),
                "expected 32/41 MPG and 5-seat capacity")

    # consumer rating 5.0 with 100% recommend
    judge.check("answer_consumer",
                contains_any(answer, ["5.0"]) and contains_int(answer, 100),
                "expected consumer rating 5.0 with 100% recommend")

    # two good + two bad points (from the frozen good/bad lists)
    good_tokens = ["Nimble handling", "Fuel economy", "Upscale cabin",
                   "Many standard features", "Satisfying acceleration"]
    bad_tokens = ["Meager passing power", "noisy on highway",
                  "Hybrid more expensive", "more expensive than key rivals",
                  "missing even in flagship", "very expensive", "Some comfort"]
    judge.check("answer_good_points",
                sum(1 for t in good_tokens if contains_any(answer, [t])) >= 2,
                "expected at least two 'good' points")
    judge.check("answer_bad_points",
                sum(1 for t in bad_tokens if contains_any(answer, [t])) >= 2,
                "expected at least two 'bad' points")

    # saved search 'Civic research' with daily alerts
    judge.check("answer_saved_search",
                contains_all(answer, ["Civic research", "daily"]),
                "expected the saved search 'Civic research' with daily alerts")

    # Accord comparison: both starting MSRPs $28,395 (Accord) / $29,700 (Camry)
    judge.check("answer_accord_msps",
                contains_price(answer, 28395) and contains_price(answer, 29700),
                "expected the Accord $28,395 and Camry $29,700 starting MSRPs")

    # DB: alice now has 2 saved searches (1 seed + 'Civic research' daily)
    check_saved_search(judge, after_db, ALICE, "Civic research", "daily")
    rows = __import__("verify_lib").saved_searches_for(after_db, ALICE)
    judge.check("alice_search_count", len(rows) == 2,
                f"searches={[(r['name'], r['alert_frequency']) for r in rows]!r}")
    check_only_tables_changed(judge, initial_db, after_db, ("saved_searches",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
