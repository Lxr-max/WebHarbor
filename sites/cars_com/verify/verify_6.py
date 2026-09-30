#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--6.

Compare the Honda Civic against the Toyota Corolla (starting MSRP, horsepower,
city/highway MPG, seating capacity, passenger volume); open both model pages
from the comparison (Civic starting price, trim count, cheapest trim, safety
rating, consumer rating + recommend %; the Corolla page — note it shows NO
consumer rating); open the Civic's listings from its model page, sort by
lowest price, save the cheapest listing as carol.d@test.com. Stateful
(carol +1 saved car).

NOTE: the ground truth assumes the model-filter round-trip fix (the review
found the SERP sort form silently dropping the `models` filter, which turned
the "cheapest Civic" into a $2,500 Nissan Rogue)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--6"
COMPARE_PATH = "/research/compare/honda-civic-vs-toyota-corolla/"
CIVIC_PAGE = "/research/honda-civic-2026/"
COROLLA_PAGE = "/research/toyota-corolla-2027/"
CHEAPEST_CIVIC = "659632f3-b6f0-4128-9e3a-1fccff084bcc"  # 2017 Honda Civic LX
CAROL = "carol.d@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, CAROL)

    judge.check("nav_compare", navigated_to(traj, COMPARE_PATH),
                f"required: {COMPARE_PATH}")
    judge.check("nav_civic_model", navigated_to(traj, CIVIC_PAGE),
                f"required: {CIVIC_PAGE}")
    judge.check("nav_corolla_model", navigated_to(traj, COROLLA_PAGE),
                f"required: {COROLLA_PAGE}")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{CHEAPEST_CIVIC}/"),
                f"required: /vehicledetail/{CHEAPEST_CIVIC[:8]}… (cheapest Civic listing)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # comparison facts: Corolla has the lower starting MSRP ($23,325 vs $24,695)
    judge.check("answer_msrp",
                contains_price(answer, 24695) and contains_price(answer, 23325),
                "expected both starting MSRPs ($24,695 Civic / $23,325 Corolla)")
    judge.check("answer_lower_msrp", contains_all(answer, ["Corolla"]),
                "expected: the Corolla has the lower starting MSRP")
    # horsepower: Corolla 169 hp vs Civic 150 hp
    judge.check("answer_horsepower",
                contains_int(answer, 150) and contains_int(answer, 169),
                "expected 150 hp (Civic) and 169 hp (Corolla)")
    # MPG: both 32 city / 41 highway (a tie)
    judge.check("answer_mpg",
                contains_all(answer, ["32"]) and contains_all(answer, ["41"]),
                "expected 32 city / 41 highway for both")
    # seating capacity 5 both; passenger volume 99 ft3 (Civic) vs 89 ft3 (Corolla)
    judge.check("answer_seating", contains_int(answer, 5),
                "expected seating capacity 5 for both")
    judge.check("answer_passenger_volume",
                contains_int(answer, 99) and contains_int(answer, 89),
                "expected passenger volumes 99 ft3 (Civic) and 89 ft3 (Corolla)")

    # Civic model page: starts at $24,695; 9 trims; cheapest trim LX CVT $24,695;
    # safety rating 5/5; consumer rating 4.4 with 75% recommend
    judge.check("answer_civic_start", contains_price(answer, 24695),
                "expected the Civic starting price $24,695")
    judge.check("answer_civic_trims", contains_int(answer, 9),
                "expected 9 trims listed")
    judge.check("answer_civic_cheapest_trim",
                contains_all(answer, ["LX CVT"]) and contains_price(answer, 24695),
                "expected the cheapest trim LX CVT at $24,695")
    judge.check("answer_civic_safety", contains_any(answer, ["5/5", "5 / 5"]),
                "expected the Civic safety rating 5/5")
    judge.check("answer_civic_consumer",
                contains_any(answer, ["4.4"]) and contains_any(answer, ["75"]),
                "expected consumer rating 4.4 with 75% recommend")

    # garage: the saved cheapest Civic ($8,971, 2017 Civic LX)
    judge.check("answer_garage_car",
                contains_all(answer, ["Honda Civic"]) and contains_price(answer, 8971),
                "expected the saved cheapest Civic ($8,971) in the garage")

    # DB: carol now has 3 saved cars (2 seed + this Civic)
    check_saved_car(judge, after_db, CAROL, CHEAPEST_CIVIC, exactly=3)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
