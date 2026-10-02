#!/usr/bin/env python3
"""Verify Parkers--6.

Help me decide whether the BMW 3 Series Saloon (2019 onwards) would be a comfortable, economical daily driver. Summarise Parkers' findings on rear passenger space, the 318d engine and running costs, with the expert overall rating and comfort score. Put that assessment alongside the average owner rating, keeping the owner and expert scores distinct.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (  # noqa: E402
    Judge, check_read_only, check_seed_contract, check_trajectory_identity,
    contains_amount, contains_amount_range, labeled_range, contains_any_phrase, contains_count,
    contains_phrase, final_answer, navigated_c4s_search, navigated_cartax_gen,
    navigated_cartax_hub, navigated_guide, navigated_insurance,
    navigated_listing_detail, navigated_news, navigated_owner_reviews,
    navigated_reg_lookup, navigated_review, navigated_review_section,
    navigated_to_path,
    navigated_shortlist, navigated_sign_in, navigated_site_search,
    navigated_specs, navigated_specs_gen, navigated_valuation_chain,
    run_verifier, shortlist_listing_ids, added_rows, removed_rows, rows_of,
    user_by_email)

TASK_ID = "Parkers--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_review", navigated_review(traj, "bmw", "3-series"),
                "required: 3 Series review overview")
    judge.check("nav_verdict", navigated_review_section(traj, "bmw", "3-series", "verdict"),
                "required: 3 Series review verdict section")
    judge.check("nav_practicality",
                navigated_review_section(traj, "bmw", "3-series", "practicality"),
                "required: 3 Series practicality section (rear space)")
    judge.check("nav_engines",
                navigated_review_section(traj, "bmw", "3-series", "engines"),
                "required: 3 Series engines section (318d)")
    judge.check("nav_ownership",
                navigated_review_section(traj, "bmw", "3-series", "mpg-running-costs"),
                "required: 3 Series ownership cost section")
    judge.check("answer_rating", contains_count(answer, 4),
                "overall rating is 4 out of 5")
    judge.check("answer_rear_space", contains_phrase(answer, "rear"),
                "the practicality point must mention rear space")
    judge.check("answer_318d", contains_phrase(answer, "318d"),
                "the engines point must mention the 318d")
    judge.check("answer_ownership_fact",
                contains_any_phrase(answer, ["mpg", "running cost", "insurance group",
                                             "road tax", "depreciation", "economy"]),
                "the ownership-cost fact must be a running-costs fact")
    judge.check("answer_comfort", contains_count(answer, 4.3),
                "comfort score from the verdict is 4.3")
    judge.check("nav_owner_reviews",
                navigated_owner_reviews(traj, "bmw", "3-series", "saloon-2019"),
                "required: 3 Series Saloon (2019 onwards) owner reviews page")
    judge.check("answer_owner_rating", contains_count(answer, 4.3),
                "owners give the 3 Series Saloon (2019 onwards) an average of 4.3")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
