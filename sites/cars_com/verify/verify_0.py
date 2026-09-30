#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--0.

Used SUV $25k-$35k, under 70k miles, within 50 miles of the default ZIP:
result count -> Good Deal count -> cheapest by lowest price -> its dealer's
Monday hours + phone -> reviews page count -> inventory count. Read-only.

Ground truth is HARDCODED below (frozen from the reviewer's independent
DOM-asserted two-round Chromium walkthrough + SQLite reads; never present in
tasks.jsonl). Deterministic only — no LLM calls.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity, check_read_only)

TASK_ID = "Cars.com--0"
CHEAPEST_ID = "353e2646-07ab-4cf3-9811-eb919af85867"   # 2021 Toyota RAV4 LE
DEALER_PATH = "/dealers/26520/rairdons-cdjr-kirkland/"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_read_only(judge, initial_db, after_db)

    # navigation gates: the SERP chain, the cheapest listing, the dealer chain
    judge.check("nav_srp_used", navigated_to(traj, "/shopping/results/"),
                "required: the used-SUV SERP")
    judge.check("nav_cheapest_listing",
                navigated_to(traj, f"/vehicledetail/{CHEAPEST_ID}/"),
                f"required: /vehicledetail/{CHEAPEST_ID[:8]}… (cheapest Good Deal SUV)")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_dealer_reviews", navigated_to(traj, DEALER_PATH + "reviews/"),
                "required: the dealer's reviews page")
    judge.check("nav_dealer_inventory", navigated_to(traj, DEALER_PATH + "inventory/"),
                "required: the dealer's inventory page")

    # counts: 249 used cars within 50 mi -> 37 after SUV+price+mileage ->
    # 22 after Good Deal (post-filter-fix semantics; frozen from walkthrough)
    judge.check("answer_count_used_50", contains_int(answer, 249),
                "expected 249 results for used cars within 50 miles")
    judge.check("answer_count_filtered", contains_int(answer, 37),
                "expected 37 results after SUV + $25k-$35k + <=70k miles")
    judge.check("answer_count_good_deal", contains_int(answer, 22),
                "expected 22 results after narrowing to Good Deal")

    # cheapest listing facts: $25,261 / 42,801 mi / Good Deal / $476/mo @ 7.0% APR
    judge.check("answer_price", contains_price(answer, 25261),
                "expected $25,261")
    judge.check("answer_mileage", contains_int(answer, 42801),
                "expected 42,801 miles")
    judge.check("answer_deal_badge", contains_any(answer, ["Good Deal"]),
                "expected the Good Deal badge")
    judge.check("answer_monthly_apr",
                contains_int(answer, 476) and contains_any(answer, ["7.0%", "7%"]),
                "expected Est. $476/mo at 7.0% APR")
    judge.check("answer_dealer_name",
                contains_all(answer, ["Rairdon", "Kirkland"]),
                "expected the dealer Rairdon's Chrysler Dodge Jeep RAM of Kirkland")
    judge.check("answer_dealer_rating", contains_any(answer, ["4.3"]),
                "expected the dealer's 4.3 rating")

    # dealer page: Monday hours 9:00am-8:00pm + a listed phone number
    judge.check("answer_monday_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["8:00"]),
                "expected Monday 9:00am-8:00pm")
    judge.check("answer_dealer_phone",
                contains_any(answer, ["471-5513", "813-8901"]),
                "expected (888) 471-5513 or (877) 813-8901")

    # reviews page: 10 reviews shown; inventory: 7 cars
    judge.check("answer_review_count", contains_int(answer, 10),
                "expected 10 reviews on the reviews page")
    judge.check("answer_inventory_count", contains_int(answer, 7),
                "expected 7 cars in the dealer's inventory")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
