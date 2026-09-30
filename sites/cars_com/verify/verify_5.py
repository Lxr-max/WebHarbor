#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--5.

Porsche Bellevue (via the dealer directory's make filter): rating + review
count + weekly sales hours + awards; the three most recent reviews; inventory
count + most expensive car; save it as bob.c@test.com, report the garage,
remove it and report what remains. Stateful (net DB delta zero — the save is
undone by the remove; the trajectory + answer carry the evidence)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, check_saved_car_absent,
                        saved_car_ids, changed_tables)

TASK_ID = "Cars.com--5"
AUDI_ID = "9d7e7c43-041e-4054-90a1-a0d03563d841"      # 2021 Audi RS 6 Avant 4.0T
DEALER_PATH = "/dealers/158590/porsche-bellevue/"
BOB = "bob.c@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, BOB)

    judge.check("nav_dealers_directory", navigated_to(traj, "/dealers/"),
                "required: the dealer directory")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_dealer_reviews", navigated_to(traj, DEALER_PATH + "reviews/"),
                "required: the dealer's reviews page")
    judge.check("nav_dealer_inventory", navigated_to(traj, DEALER_PATH + "inventory/"),
                "required: Porsche Bellevue's inventory page")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{AUDI_ID}/"),
                f"required: /vehicledetail/{AUDI_ID[:8]}… (the most expensive car)")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page (at least once)")

    # dealer page: 4.9 with 1,266 reviews; 8 awards; Mon-Sat 9:00am-8:00pm
    judge.check("answer_rating_reviews",
                contains_any(answer, ["4.9"]) and contains_any(answer, ["1,266", "1266"]),
                "expected rating 4.9 with 1,266 reviews")
    judge.check("answer_awards", contains_int(answer, 8),
                "expected 8 awards")
    judge.check("answer_weekly_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["8:00"]),
                "expected weekly sales hours 9:00am-8:00pm (Mon-Sat)")

    # three most recent reviews: Max B, Huong, Bill B — all 5.0, dated
    # 2026-09-19 / 2026-09-18 / 2026-09-18
    judge.check("answer_recent_reviews",
                contains_all(answer, ["Max B", "Huong", "Bill B"]),
                "expected the three most recent review authors")
    judge.check("answer_recent_review_dates",
                contains_all(answer, ["2026-09-19", "2026-09-18"]),
                "expected the review dates 2026-09-19 and 2026-09-18")

    # inventory: 8 cars; most expensive: 2021 Audi RS 6 Avant 4.0T $92,990, 41,469 mi
    judge.check("answer_inventory_count", contains_int(answer, 8),
                "expected 8 cars listed")
    judge.check("answer_most_expensive",
                contains_all(answer, ["Audi RS 6"]) and contains_price(answer, 92990),
                "expected the most expensive car: Audi RS 6 Avant 4.0T at $92,990")
    judge.check("answer_most_expensive_mileage", contains_int(answer, 41469),
                "expected 41,469 miles")

    # garage: the saved Audi shown, then removed — the remaining three cars
    judge.check("answer_garage_showed_audi",
                contains_all(answer, ["Audi RS 6"]) and contains_price(answer, 92990),
                "expected the garage to show the saved Audi RS 6")
    judge.check("answer_garage_remaining",
                contains_all(answer, ["F-150"]) and contains_all(answer, ["Model 3"]),
                "expected the remaining saved cars (F-150s + Tesla Model 3)")

    # DB: net zero — the Audi must NOT be among bob's saved cars at the end
    check_saved_car_absent(judge, after_db, BOB, AUDI_ID)
    ids = saved_car_ids(after_db, BOB)
    judge.check("bob_saved_count", len(ids) == 3,
                f"saved_cars={[i[:8] for i in ids]!r}")
    changed = changed_tables(initial_db, after_db)
    judge.check("db_net_clean", not changed,
                f"changed_tables={changed!r} (save + remove must cancel out)")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
