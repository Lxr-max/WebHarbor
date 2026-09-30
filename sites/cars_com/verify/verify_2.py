#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--2.

New Toyota RAV4s: result count + lowest/highest prices on page 1; cheapest
listing facts; its dealer's Monday hours; the payment calculator for that price
(good credit, $4,000 down, 60 months); the RAV4 research page facts.
Read-only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity, check_read_only)

TASK_ID = "Cars.com--2"
RAV4_ID = "6251e2c0-b153-444f-8d17-ebbec873f8c9"      # 2026 Toyota RAV4 LE
DEALER_PATH = "/dealers/5382245/marysville-toyota/"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_read_only(judge, initial_db, after_db)

    judge.check("nav_srp_rav4", navigated_to(traj, "/shopping/results/"),
                "required: the new-RAV4 SERP")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{RAV4_ID}/"),
                f"required: /vehicledetail/{RAV4_ID[:8]}… (cheapest new RAV4)")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_calculator", navigated_to(traj, "/car-loan-calculator/"),
                "required: the payment calculator")
    judge.check("nav_research", navigated_to(traj, "/research/toyota-rav4-2025/"),
                "required: the RAV4 research page")

    # counts and page-1 price range
    judge.check("answer_count_rav4", contains_int(answer, 24),
                "expected 24 new RAV4 results")
    judge.check("answer_lowest_price", contains_price(answer, 35683),
                "expected the lowest price $35,683 on page 1")
    judge.check("answer_highest_price", contains_price(answer, 62543),
                "expected the highest price $62,543 on page 1")

    # cheapest listing facts: 2 miles / $673/mo @ 7.0% / Marysville Toyota
    judge.check("answer_mileage", contains_int(answer, 2),
                "expected 2 miles")
    judge.check("answer_monthly_apr",
                contains_int(answer, 673) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $673/mo at 7.0% APR")
    judge.check("answer_dealer", contains_all(answer, ["Marysville Toyota"]),
                "expected the dealer Marysville Toyota")
    judge.check("answer_monday_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["7:00"]),
                "expected Monday 9:00am-7:00pm")

    # calculator for $35,683, good credit, $4,000 down, 60 months:
    # monthly $700, total interest $6,647
    judge.check("answer_calc_monthly", contains_price(answer, 700),
                "expected the $700/mo calculator estimate")
    judge.check("answer_calc_interest", contains_any(answer, ["6,647", "6647"]),
                "expected $6,647 total interest")

    # research page: starts at $29,800; 29 trims; cheapest trim LE FWD (Natl)
    # $29,800 at 27/35 MPG; consumer rating 4.5 with 81% recommend
    judge.check("answer_research_start", contains_price(answer, 29800),
                "expected the RAV4 research starting price $29,800")
    judge.check("answer_trim_count", contains_int(answer, 29),
                "expected 29 trims listed")
    judge.check("answer_cheapest_trim",
                contains_all(answer, ["LE FWD"]) and contains_price(answer, 29800),
                "expected the cheapest trim LE FWD (Natl) at $29,800")
    judge.check("answer_trim_mpg",
                contains_all(answer, ["27"]) and contains_all(answer, ["35"]),
                "expected 27 city / 35 highway MPG")
    judge.check("answer_consumer_rating",
                contains_any(answer, ["4.5"]) and contains_any(answer, ["81"]),
                "expected consumer rating 4.5 with 81% recommend")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
