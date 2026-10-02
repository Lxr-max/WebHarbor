#!/usr/bin/env python3
"""Verify Parkers--12.

I'm considering the updated Renault 5 E-Tech as an everyday electric car. Use Parkers' 2027 update news to compare the official WLTP range of its two battery sizes and the improvement over the earlier figures. Put that range upgrade in a running-cost context using the expert review's charging advice, the insurance group range and the cheapest version's price when new.
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
    navigated_shortlist, navigated_sign_in, navigated_site_search,
    navigated_specs, navigated_specs_gen, navigated_valuation_chain,
    run_verifier, shortlist_listing_ids, added_rows, removed_rows, rows_of,
    user_by_email)

TASK_ID = "Parkers--12"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_news", navigated_news(traj, "renault-5-e-tech-updated-for-2027"),
                "required: the Renault 5 E-Tech 2027 update news article")
    judge.check("answer_40kwh", contains_count(answer, 197),
                "40kWh model WLTP range is 197 miles")
    judge.check("answer_52kwh", contains_count(answer, 259),
                "52kWh model WLTP range is 259 miles")
    judge.check("answer_improvement", contains_count(answer, 11),
                "range improved by 11 miles")
    judge.check("nav_ownership",
                navigated_review_section(traj, "renault", "5-e-tech", "mpg-running-costs"),
                "required: 5 E-Tech ownership cost section (running-costs fact)")
    judge.check("answer_running_costs_fact",
                contains_any_phrase(answer, ["insurance group", "mpg", "running cost",
                                             "road tax", "charging"]),
                "a running-costs fact from the ownership cost section must be reported")
    judge.check("nav_insurance",
                navigated_insurance(traj, "renault", "5-e-tech", "hatchback-2025"),
                "required: 5 E-Tech insurance-groups page")
    judge.check("answer_insurance_range",
                contains_count(answer, 18) and contains_count(answer, 23),
                "the 5 E-Tech's insurance groups run from 18 to 23")
    judge.check("nav_5etech_specs",
                navigated_specs_gen(traj, "renault", "5-e-tech", "hatchback-2025"),
                "required: 5 E-Tech specs page (cheapest price when new)")
    judge.check("answer_price_new", contains_amount(answer, 22995),
                "the cheapest 5 E-Tech version costs £22,995 when new")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
