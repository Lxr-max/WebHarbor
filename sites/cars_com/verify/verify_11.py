#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--11.

Budget car search: used cars under $15,000 with at most 80,000 miles within 20
miles, sorted by lowest mileage — result count; the three lowest-mileage
listings' prices and mileages; open the lowest-mileage one (dealer, exterior
color, first two lines of seller's notes, monthly estimate + APR, deal badge);
save it as carol.d@test.com and report the garage incl. the total number of
saved cars. Stateful (carol +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--11"
ALTIMA_ID = "e55c5fe0-ceff-406c-9ee7-4e2d2b263ba4"     # 2017 Nissan Altima 2.5 S
CAROL = "carol.d@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, CAROL)

    judge.check("nav_srp", navigated_to(traj, "/shopping/results/"),
                "required: the budget-car SERP")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{ALTIMA_ID}/"),
                f"required: /vehicledetail/{ALTIMA_ID[:8]}… (the lowest-mileage car)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # count: 3 results
    judge.check("answer_count", contains_int(answer, 3),
                "expected 3 results")

    # three lowest-mileage listings: Altima $14,990/55,758; MINI $12,500/64,000;
    # Sportage $12,900/76,859
    judge.check("answer_three_prices",
                contains_price(answer, 14990) and contains_price(answer, 12500)
                and contains_price(answer, 12900),
                "expected the three prices $14,990 / $12,500 / $12,900")
    judge.check("answer_three_mileages",
                contains_int(answer, 55758) and contains_int(answer, 64000)
                and contains_int(answer, 76859),
                "expected the three mileages 55,758 / 64,000 / 76,859")

    # lowest-mileage listing: Lee Johnson Mazda of Kirkland; Brilliant Silver;
    # seller's notes start '+++ LOW MILEAGE +++ This 2017 Nissan Altima 2.5 S';
    # Est. $283/mo at 7.0% APR; Fair Deal badge
    judge.check("answer_dealer", contains_all(answer, ["Lee Johnson Mazda of Kirkland"]),
                "expected the dealer Lee Johnson Mazda of Kirkland")
    judge.check("answer_ext_color", contains_all(answer, ["Brilliant Silver"]),
                "expected the Brilliant Silver exterior color")
    judge.check("answer_notes",
                contains_any(answer, ["LOW MILEAGE", "low mileage"])
                and contains_all(answer, ["Altima"]),
                "expected the seller's-notes opening (LOW MILEAGE / this 2017 Altima)")
    judge.check("answer_monthly_apr",
                contains_int(answer, 283) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $283/mo at 7.0% APR")
    judge.check("answer_deal_badge", contains_any(answer, ["Fair Deal"]),
                "expected the Fair Deal badge")

    # garage: 3 saved cars total (2 seed + this Altima)
    judge.check("answer_garage_total", contains_int(answer, 3),
                "expected the garage to show a total of 3 saved cars")

    # DB: carol now has 3 saved cars (2 seed + this Altima)
    check_saved_car(judge, after_db, CAROL, ALTIMA_ID, exactly=3)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
