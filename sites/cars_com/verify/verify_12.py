#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--12.

Used cars with manual transmission within 50 miles: result count; narrow to
under $25,000 (new count); cheapest + most expensive titles and prices on
page 1; open the cheapest (mileage, exterior color, dealer name + rating,
monthly estimate + APR); save it as bob.c@test.com and report the garage.
Stateful (bob +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--12"
JETTA_ID = "cd095082-28dd-4fa9-9ffb-973809872ce6"      # 2021 Volkswagen Jetta 1.4T S
BOB = "bob.c@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, BOB)

    judge.check("nav_srp", navigated_to(traj, "/shopping/results/"),
                "required: the manual-transmission SERP")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{JETTA_ID}/"),
                f"required: /vehicledetail/{JETTA_ID[:8]}… (the cheapest manual car)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # counts: 12 manual cars within 50 miles; 3 under $25,000
    judge.check("answer_count_manual_50", contains_int(answer, 12),
                "expected 12 manual-transmission results within 50 miles")
    judge.check("answer_count_under25k", contains_int(answer, 3),
                "expected 3 results under $25,000")

    # cheapest + most expensive on page 1: Jetta 1.4T S $13,748;
    # Ford Focus RS $23,830
    judge.check("answer_cheapest",
                contains_all(answer, ["Jetta"]) and contains_price(answer, 13748),
                "expected the cheapest: Volkswagen Jetta 1.4T S at $13,748")
    judge.check("answer_most_expensive",
                contains_all(answer, ["Focus RS"]) and contains_price(answer, 23830),
                "expected the most expensive: Ford Focus RS at $23,830")

    # opened cheapest: 84,388 mi; Black; AutoNation Ford Bellevue 4.8;
    # Est. $259/mo at 7.0% APR
    judge.check("answer_mileage", contains_int(answer, 84388),
                "expected 84,388 miles")
    judge.check("answer_ext_color", contains_all(answer, ["Black"]),
                "expected the Black exterior color")
    judge.check("answer_dealer_rating",
                contains_all(answer, ["AutoNation Ford Bellevue"]) and contains_any(answer, ["4.8"]),
                "expected AutoNation Ford Bellevue with rating 4.8")
    judge.check("answer_monthly_apr",
                contains_int(answer, 259) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $259/mo at 7.0% APR")

    # garage: the saved Jetta
    judge.check("answer_garage_car", contains_all(answer, ["Jetta"]),
                "expected the saved Jetta in the garage")

    # DB: bob now has 4 saved cars (3 seed + the Jetta)
    check_saved_car(judge, after_db, BOB, JETTA_ID, exactly=4)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
