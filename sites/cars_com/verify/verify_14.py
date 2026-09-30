#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--14.

Log in as bob.c@test.com and open the garage: every saved car's title + price,
every saved search's name + alert frequency; open the first saved search's
link and report how many results it finds; value bob's Tesla Model 3 Long
Range AWD with the Instant Cash Offer tool (38,000 miles, white exterior, one
key, original owner) — initial estimated range + final offer range; report the
Instant Offer requests area; remove one saved car and report which remain.
Stateful (bob: offer_requests +1, saved_cars 3 -> 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, saved_car_ids,
                        offer_requests_for, changed_tables)

TASK_ID = "Cars.com--14"
BOB = "bob.c@test.com"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, BOB)

    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")
    judge.check("nav_saved_search", navigated_to(traj, "/shopping/results/"),
                "required: the first saved search's SERP")
    judge.check("nav_offer_start", navigated_to(traj, "/sell/instant-offer/"),
                "required: the Instant Cash Offer start page")
    judge.check("nav_offer_result", navigated_to(traj, "/sell/instant-offer/offer/"),
                "required: the offer result page")

    # garage: three saved cars — 2025 Ford F-150 XLT $46,377; 2026 Ford F-150
    # Lariat $66,456; 2022 Tesla Model 3 Performance $34,691 — plus the saved
    # search 'New Toyota RAV4 near Seattle' with weekly alerts
    judge.check("answer_saved_cars",
                contains_price(answer, 46377) and contains_price(answer, 66456)
                and contains_price(answer, 34691),
                "expected the three saved cars' prices $46,377 / $66,456 / $34,691")
    judge.check("answer_saved_search",
                contains_all(answer, ["New Toyota RAV4 near Seattle", "weekly"]),
                "expected the saved search 'New Toyota RAV4 near Seattle' (weekly)")

    # the first saved search's link: 24 results
    judge.check("answer_search_results", contains_int(answer, 24),
                "expected the saved search to find 24 results")

    # Tesla Model 3 Long Range AWD valuation: initial $17,500 - $20,200;
    # final offer $17,450 - $20,150
    judge.check("answer_initial_range",
                contains_int(answer, 17500) and contains_int(answer, 20200),
                "expected the initial estimate $17,500 - $20,200")
    judge.check("answer_final_range",
                contains_int(answer, 17450) and contains_int(answer, 20150),
                "expected the final offer $17,450 - $20,150")

    # the Instant Offer requests area shows the saved request; after removing
    # one saved car, two remain
    judge.check("answer_offers_area",
                contains_any(answer, ["17,450", "17450"]) and contains_any(answer, ["Model 3", "Tesla"]),
                "expected the Instant Offer requests area to show the Model 3 offer")
    judge.check("answer_two_remain",
                contains_any(answer, ["remain", "remaining", "left", "still", "two"]),
                "expected the report of the two remaining saved cars")

    # DB: bob has exactly 2 saved cars left; exactly 1 offer request row for
    # the Model 3 at $17,450 - $20,150 with 38,000 miles
    ids = saved_car_ids(after_db, BOB)
    judge.check("bob_two_saved_cars", len(ids) == 2,
                f"saved_cars={[i[:8] for i in ids]!r}")
    offers = offer_requests_for(after_db, BOB)
    judge.check("one_offer_request", len(offers) == 1,
                f"offers={len(offers)}")
    if offers:
        o = offers[0]
        judge.check("offer_vehicle",
                    "model 3" in (o["model"] or "").casefold() and o["year"] == 2021,
                    f"vehicle={o['year']} {o['make']} {o['model']}")
        judge.check("offer_values",
                    o["offer_low"] == 17450 and o["offer_high"] == 20150,
                    f"offer={o['offer_low']}-{o['offer_high']}")
        judge.check("offer_mileage", o["mileage"] == 38000,
                    f"mileage={o['mileage']}")
    changed = changed_tables(initial_db, after_db)
    judge.check("only_expected_tables_changed",
                set(changed) <= {"saved_cars", "offer_requests"},
                f"changed_tables={changed!r}")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
