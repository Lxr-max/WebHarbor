#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--10.

Electric cars for sale: result count; narrow to under $30,000; cheapest EV's
price/mileage/dealer; open it (monthly estimate + APR, exterior color, two
features); open the most expensive EV on the first page (mileage + dealer);
save the cheapest EV as alice.j@test.com and report the garage's saved-cars
count. Stateful (alice +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--10"
TESLA_ID = "62d7f3ec-a98b-4cbe-9883-0bd314bd796b"      # 2018 Tesla Model 3 Long Range
MOST_EXPENSIVE_ID = "361af1d6-5669-4843-ad54-9f597ad57079"  # 2023 Model 3 Standard Range
ALICE = "alice.j@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, ALICE)

    judge.check("nav_ev_serp", navigated_to(traj, "/shopping/results/"),
                "required: the electric-cars SERP")
    judge.check("nav_cheapest", navigated_to(traj, f"/vehicledetail/{TESLA_ID}/"),
                f"required: /vehicledetail/{TESLA_ID[:8]}… (the cheapest EV)")
    judge.check("nav_most_expensive", navigated_to(traj, f"/vehicledetail/{MOST_EXPENSIVE_ID}/"),
                f"required: /vehicledetail/{MOST_EXPENSIVE_ID[:8]}… (most expensive EV on page 1)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # counts: 101 EVs; 31 under $30,000
    judge.check("answer_count_ev", contains_int(answer, 101),
                "expected 101 electric cars")
    judge.check("answer_count_under30k", contains_int(answer, 31),
                "expected 31 results under $30,000")

    # cheapest EV: $19,995 / 59,722 mi / AutoNation Ford Bellevue
    judge.check("answer_cheapest_price", contains_price(answer, 19995),
                "expected the cheapest EV at $19,995")
    judge.check("answer_cheapest_mileage", contains_int(answer, 59722),
                "expected 59,722 miles")
    judge.check("answer_cheapest_dealer", contains_all(answer, ["AutoNation Ford Bellevue"]),
                "expected the dealer AutoNation Ford Bellevue")

    # opened cheapest: Est. $377/mo at 7.0% APR; Black exterior; two features
    judge.check("answer_monthly_apr",
                contains_int(answer, 377) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $377/mo at 7.0% APR")
    judge.check("answer_ext_color", contains_all(answer, ["Black"]),
                "expected the Black exterior color")
    judge.check("answer_features",
                contains_any(answer, ["Heated Seats", "Keyless Entry",
                                      "Navigation System", "Alloy Wheels",
                                      "Sunroof", "Premium Sound"]),
                "expected at least two features from the feature list")

    # most expensive EV on page 1: $29,964 / 22,732 mi / Tonkin Gladstone Hyundai
    judge.check("answer_most_expensive",
                contains_price(answer, 29964) and contains_int(answer, 22732),
                "expected the most expensive page-1 EV at $29,964 with 22,732 miles")
    judge.check("answer_most_expensive_dealer",
                contains_all(answer, ["Tonkin Gladstone Hyundai"]),
                "expected the dealer Tonkin Gladstone Hyundai")

    # garage: saved-cars count 4 (3 seed + the saved EV)
    judge.check("answer_garage_count", contains_int(answer, 4),
                "expected the garage to show 4 saved cars")

    # DB: alice now has 4 saved cars (3 seed + this EV)
    check_saved_car(judge, after_db, ALICE, TESLA_ID, exactly=4)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
