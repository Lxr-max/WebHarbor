#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--9.

Cars for sale by owner: result count; cheapest one's price/mileage/location;
whether any listing carries a deal badge; narrow to under $20,000, sort by
lowest price, open the cheapest (exterior color + the seller area of its
page); open the second-cheapest too (price + mileage); save the cheaper one
from the results page as dana.k@test.com and report the garage. Stateful
(dana +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--9"
ROGUE_ID = "7d9719d7-be0f-4ff2-8f0f-70a280cd475b"      # 2013 Nissan Rogue S
FUSION_ID = "f9d51079-7577-4908-8bf8-7b9029302bdf"     # 2009 Ford Fusion SE
DANA = "dana.k@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, DANA)

    judge.check("nav_fsbo_serp", navigated_to(traj, "/shopping/results/"),
                "required: the for-sale-by-owner SERP")
    judge.check("nav_cheapest", navigated_to(traj, f"/vehicledetail/{ROGUE_ID}/"),
                f"required: /vehicledetail/{ROGUE_ID[:8]}… (the cheapest FSBO car)")
    judge.check("nav_second_cheapest", navigated_to(traj, f"/vehicledetail/{FUSION_ID}/"),
                f"required: /vehicledetail/{FUSION_ID[:8]}… (the second-cheapest)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # counts: 24 FSBO listings; 16 under $20,000
    judge.check("answer_count_fsbo", contains_int(answer, 24),
                "expected 24 results")
    judge.check("answer_count_under20k", contains_int(answer, 16),
                "expected 16 results under $20,000")

    # cheapest: $2,500 / 187,000 mi / Seattle, WA
    judge.check("answer_cheapest_price", contains_price(answer, 2500),
                "expected the cheapest at $2,500")
    judge.check("answer_cheapest_mileage", contains_int(answer, 187000),
                "expected 187,000 miles")
    judge.check("answer_cheapest_location", contains_all(answer, ["Seattle"]),
                "expected the Seattle, WA location")
    # no listing carries a deal badge in the FSBO set
    judge.check("answer_no_badge",
                contains_any(answer, ["no deal badge", "none", "no", "not"]),
                "expected: no listing carries a deal badge")

    # cheapest listing page: Gray exterior; the seller area shows a private
    # seller (no dealership Seller's-info block on private listings)
    judge.check("answer_ext_color", contains_all(answer, ["Gray"]),
                "expected the Gray exterior color")
    judge.check("answer_seller_area",
                contains_any(answer, ["Private seller", "private seller", "no seller"]),
                "expected the private-seller area (no dealership block)")

    # second-cheapest: $3,199 / 198,860 mi (2009 Ford Fusion SE)
    judge.check("answer_second_price", contains_price(answer, 3199),
                "expected the second-cheapest at $3,199")
    judge.check("answer_second_mileage", contains_int(answer, 198860),
                "expected 198,860 miles")

    # garage: the saved Rogue
    judge.check("answer_garage_car", contains_all(answer, ["Nissan Rogue"]),
                "expected the saved Nissan Rogue in the garage")

    # DB: dana now has 3 saved cars (2 seed + the Rogue)
    check_saved_car(judge, after_db, DANA, ROGUE_ID, exactly=3)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
