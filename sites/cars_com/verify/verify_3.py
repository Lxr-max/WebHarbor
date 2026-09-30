#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--3.

Certified Toyotas: result count; narrow to <=40,000 miles and 2020-or-newer;
cheapest listing facts incl. the CPO program's basic warranty terms and the
maximum vehicle age and mileage covered, its history summary and deal badge;
then the dealership page (Monday hours + phone), reviews page count, and the
inventory filtered to certified cars. Read-only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity, check_read_only)

TASK_ID = "Cars.com--3"
BZ4X_ID = "ffb78a76-dcb7-4c49-9fed-ebf0a56f713a"      # 2023 Toyota bZ4X Limited
DEALER_PATH = "/dealers/5382245/marysville-toyota/"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_read_only(judge, initial_db, after_db)

    judge.check("nav_srp_certified", navigated_to(traj, "/shopping/results/"),
                "required: the certified-Toyota SERP")
    judge.check("nav_listing", navigated_to(traj, f"/vehicledetail/{BZ4X_ID}/"),
                f"required: /vehicledetail/{BZ4X_ID[:8]}… (cheapest certified Toyota)")
    judge.check("nav_dealer_page", navigated_to(traj, DEALER_PATH),
                f"required: {DEALER_PATH}")
    judge.check("nav_dealer_reviews", navigated_to(traj, DEALER_PATH + "reviews/"),
                "required: the dealer's reviews page")
    judge.check("nav_dealer_inventory", navigated_to(traj, DEALER_PATH + "inventory/"),
                "required: the dealer's inventory page")

    # counts: 8 certified Toyotas -> 7 after <=40k miles + 2020-or-newer
    judge.check("answer_count_certified", contains_int(answer, 8),
                "expected 8 certified Toyota results")
    judge.check("answer_count_narrowed", contains_int(answer, 7),
                "expected 7 results after the mileage + year narrowing")

    # cheapest listing: $26,783 / 21,763 mi / Marysville Toyota / Good Deal
    judge.check("answer_price", contains_price(answer, 26783),
                "expected $26,783")
    judge.check("answer_mileage", contains_int(answer, 21763),
                "expected 21,763 miles")
    judge.check("answer_dealer", contains_all(answer, ["Marysville Toyota"]),
                "expected the dealer Marysville Toyota")
    judge.check("answer_deal_badge", contains_any(answer, ["Good Deal"]),
                "expected the Good Deal badge")

    # CPO program: basic warranty 12 months/12,000 miles; max age/mileage
    # 7 years / less than 85,000 miles
    judge.check("answer_cpo_basic_warranty",
                contains_all(answer, ["12"]) and contains_any(answer, ["12,000", "12000", "12, 000"]),
                "expected the basic warranty 12 months/12,000 miles "
                "(the page renders '12, 000' verbatim from the upstream capture)")
    judge.check("answer_cpo_max_age_mileage",
                contains_all(answer, ["7 years"]) and contains_any(answer, ["85,000", "85000"]),
                "expected maximum 7 years / less than 85,000 miles")

    # history summary: 1 owner, 0 accidents, Clean title
    judge.check("answer_history",
                contains_any(answer, ["1 owner", "one owner", "Owner 1"])
                and contains_any(answer, ["0 accidents", "no accidents", "Accidents 0"])
                and contains_any(answer, ["Clean"]),
                "expected 1 owner, 0 accidents, Clean title")

    # dealer page: Monday 9:00am-7:00pm + (360) 474-4089
    judge.check("answer_monday_hours",
                contains_all(answer, ["9:00"]) and contains_all(answer, ["7:00"]),
                "expected Monday 9:00am-7:00pm")
    judge.check("answer_dealer_phone", contains_any(answer, ["474-4089"]),
                "expected (360) 474-4089")

    # reviews page: 10 reviews; certified inventory: 3 cars
    judge.check("answer_review_count", contains_int(answer, 10),
                "expected 10 reviews on the reviews page")
    judge.check("answer_certified_inventory", contains_int(answer, 3),
                "expected 3 certified cars in the dealer's inventory")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
