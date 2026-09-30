#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--1.

Used Honda Civics within 50 miles: result count; Good Deal; lowest-mileage
listing facts; save it as alice.j@test.com and report the garage's saved-cars
area + the saved search stored there. Stateful (alice +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--1"
CIVIC_ID = "e03ee3c5-5786-4477-8c8d-afeb8e16f93f"      # 2025 Honda Civic Sport
ALICE = "alice.j@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, ALICE)

    judge.check("nav_srp_civic", navigated_to(traj, "/shopping/results/"),
                "required: the used-Civic SERP")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{CIVIC_ID}/"),
                f"required: /vehicledetail/{CIVIC_ID[:8]}… (lowest-mileage Good Deal Civic)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # count: 16 used Civics within 50 miles
    judge.check("answer_count_civic_50", contains_int(answer, 16),
                "expected 16 results")

    # listing facts: $27,969 / 10,093 mi / $527/mo @ 7.0% / A Urban Gray Pearl
    judge.check("answer_price", contains_price(answer, 27969),
                "expected $27,969")
    judge.check("answer_mileage", contains_int(answer, 10093),
                "expected 10,093 miles")
    judge.check("answer_monthly_apr",
                contains_int(answer, 527) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $527/mo at 7.0% APR")
    judge.check("answer_ext_color",
                contains_any(answer, ["Urban Gray Pearl", "Urban Gray"]),
                "expected the A Urban Gray Pearl exterior color")
    judge.check("answer_dealer", contains_all(answer, ["Kia of Everett"]),
                "expected the dealer Kia of Everett")
    judge.check("answer_dealer_rating", contains_any(answer, ["4.7"]),
                "expected the dealer's 4.7 star rating")

    # garage: the saved Civic + the seed saved search 'Used Honda Civics under $25k' (daily)
    judge.check("answer_garage_car", contains_all(answer, ["2025 Honda Civic Sport"]),
                "expected the saved 2025 Honda Civic Sport in the garage")
    judge.check("answer_garage_search",
                contains_all(answer, ["Used Honda Civics under $25k", "daily"]),
                "expected the saved search 'Used Honda Civics under $25k' with daily alerts")

    # DB: alice now has 4 saved cars (3 seed + this Civic); only saved_cars changed
    check_saved_car(judge, after_db, ALICE, CIVIC_ID, exactly=4)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
