#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--16.

Auburn Chevrolet's inventory page (via the dealer directory's make filter):
total cars; filter to used cars (count + cheapest/most expensive titles and
prices); open the cheapest used car (mileage, deal badge, exterior color);
open its dealership's page from that listing (About opening line + Monday
hours); save the cheapest used car as carol.d@test.com and report the garage.
Stateful (carol +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--16"
EXPRESS_ID = "3c922896-8642-4c15-afbb-c5d204c5f66f"     # 2017 Chevrolet Express 2500 Work Van
DEALER_PATH = "/dealers/158531/auburn-chevrolet/"
CAROL = "carol.d@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, CAROL)

    judge.check("nav_dealers_directory", navigated_to(traj, "/dealers/"),
                "required: the dealer directory (make filter)")
    judge.check("nav_inventory", navigated_to(traj, DEALER_PATH + "inventory/"),
                f"required: {DEALER_PATH}inventory/")
    judge.check("nav_cheapest", navigated_to(traj, f"/vehicledetail/{EXPRESS_ID}/"),
                f"required: /vehicledetail/{EXPRESS_ID[:8]}… (the cheapest used car)")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # inventory counts: 23 cars; 5 used
    judge.check("answer_count_all", contains_int(answer, 23),
                "expected 23 cars listed")
    judge.check("answer_count_used", contains_int(answer, 5),
                "expected 5 used cars")

    # cheapest used: 2017 Chevrolet Express 2500 Work Van $11,911;
    # most expensive used: 2025 Chevrolet Silverado 1500 LT $37,166
    judge.check("answer_cheapest_used",
                contains_all(answer, ["Express 2500"]) and contains_price(answer, 11911),
                "expected the cheapest used: Express 2500 Work Van at $11,911")
    judge.check("answer_most_expensive_used",
                contains_all(answer, ["Silverado 1500"]) and contains_price(answer, 37166),
                "expected the most expensive used: Silverado 1500 LT at $37,166")

    # opened cheapest: 180,510 mi; Good Deal badge; A Summit White exterior
    judge.check("answer_mileage", contains_int(answer, 180510),
                "expected 180,510 miles")
    judge.check("answer_badge", contains_any(answer, ["Good Deal"]),
                "expected the Good Deal badge")
    judge.check("answer_ext_color", contains_all(answer, ["Summit White"]),
                "expected the A Summit White exterior color")

    # dealership page: About opening line 'Welcome to Auburn Chevrolet where
    # Total Customer Satisfaction is our top priority.'; Monday 9:00am-8:00pm
    judge.check("answer_about",
                contains_all(answer, ["Welcome to Auburn Chevrolet"]),
                "expected the About opening line")
    judge.check("answer_monday_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["8:00"]),
                "expected Monday 9:00am-8:00pm")

    # garage: the saved Express
    judge.check("answer_garage", contains_all(answer, ["Express 2500"]),
                "expected the saved Express 2500 in the garage")

    # DB: carol now has 3 saved cars (2 seed + the Express)
    check_saved_car(judge, after_db, CAROL, EXPRESS_ID, exactly=3)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
