#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--15.

Certified Ford Escapes: open the 2025 Escape ST-Line Select from the
Shorewood, Illinois dealership — price, mileage, deal badge, good-deal range,
every price-history row with dates, above/below the good-deal range; open the
other Escape and say which is cheaper; from the Shorewood listing open its
dealership's page for Monday hours; save the Shorewood car as
dana.k@test.com and report its title + price in the garage. Stateful
(dana +1 saved car)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car,
                        check_only_tables_changed)

TASK_ID = "Cars.com--15"
SHOREWOOD_ID = "2d33ae91-4eaa-4e88-98aa-658bb3281fe5"   # 2025 Escape ST-Line Select (Shorewood)
AUBURN_ID = "c7c1b0ee-be77-4834-ab80-df3cebc55ae5"      # the other Escape (Auburn Chevrolet)
DEALER_PATH = "/dealers/936940120/ron_tirapelli_ford/"
DANA = "dana.k@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, DANA)

    judge.check("nav_srp", navigated_to(traj, "/shopping/results/"),
                "required: the certified-Escape SERP")
    judge.check("nav_shorewood", navigated_to(traj, f"/vehicledetail/{SHOREWOOD_ID}/"),
                f"required: /vehicledetail/{SHOREWOOD_ID[:8]}… (the Shorewood Escape)")
    judge.check("nav_other", navigated_to(traj, f"/vehicledetail/{AUBURN_ID}/"),
                f"required: /vehicledetail/{AUBURN_ID[:8]}… (the other Escape)")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # Shorewood Escape: $24,546 / 50,665 mi / Fair Deal badge
    judge.check("answer_price", contains_price(answer, 24546),
                "expected $24,546")
    judge.check("answer_mileage", contains_int(answer, 50665),
                "expected 50,665 miles")
    judge.check("answer_badge", contains_any(answer, ["Fair Deal"]),
                "expected the Fair Deal badge")

    # good-deal range $21,672 - $24,104; the current price sits ABOVE it
    judge.check("answer_good_deal_range",
                contains_int(answer, 21672) and contains_int(answer, 24104),
                "expected the good-deal range $21,672 - $24,104")
    judge.check("answer_above_range", contains_any(answer, ["above"]),
                "expected: the current price sits above the good-deal range")

    # price history rows: 09/18/26 -$200 -> $24,546; 08/31/26 Listed $24,746
    judge.check("answer_history_rows",
                contains_all(answer, ["09/18/26", "08/31/26"])
                and contains_price(answer, 24546) and contains_price(answer, 24746),
                "expected both price-history rows (09/18/26 $24,546; 08/31/26 $24,746)")

    # the other Escape (Auburn) is cheaper: $22,666
    judge.check("answer_other_cheaper",
                contains_price(answer, 22666) and contains_any(answer, ["cheaper", "Auburn"]),
                "expected: the other Escape (Auburn, $22,666) is cheaper")

    # Ron Tirapelli Ford Monday hours: 9am - 8pm
    judge.check("answer_monday_hours",
                contains_all(answer, ["9"]) and contains_all(answer, ["8"]),
                "expected Monday 9am - 8pm")

    # garage: the saved Shorewood Escape's title + price
    judge.check("answer_garage",
                contains_all(answer, ["Escape"]) and contains_price(answer, 24546),
                "expected the saved Escape at $24,546 in the garage")

    # DB: dana now has 3 saved cars (2 seed + the Shorewood Escape)
    check_saved_car(judge, after_db, DANA, SHOREWOOD_ID, exactly=3)
    check_only_tables_changed(judge, initial_db, after_db, ("saved_cars",))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
