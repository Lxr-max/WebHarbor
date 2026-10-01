#!/usr/bin/env python3
"""Verify Parkers--3.

We're choosing between a Skoda Kodiaq 1.5 TSI e-TEC SE 5dr DSG and a Hyundai Tucson 1.6T 150 Advance 5d for a family with two dogs and a pushchair. Compare the luggage capacities on their Parkers spec pages and recommend the one with the bigger boot, giving both capacities and the difference in litres.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (  # noqa: E402
    Judge, entity_number, check_read_only, check_seed_contract, check_trajectory_identity,
    contains_amount, contains_amount_range, labeled_range, contains_any_phrase, contains_count,
    contains_phrase, final_answer, navigated_c4s_search, navigated_cartax_gen,
    navigated_cartax_hub, navigated_guide, navigated_insurance,
    navigated_listing_detail, navigated_news, navigated_owner_reviews,
    navigated_reg_lookup, navigated_review, navigated_review_section,
    navigated_shortlist, navigated_sign_in, navigated_site_search,
    navigated_specs, navigated_specs_gen, navigated_valuation_chain,
    run_verifier, shortlist_listing_ids, added_rows, removed_rows, rows_of,
    user_by_email)

TASK_ID = "Parkers--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_kodiaq_specs",
                navigated_specs(traj, "skoda", "kodiaq", "suv-2024",
                                ["15-tsi-e-tec-se-5dr-dsg"]),
                "required: Kodiaq 1.5 TSI e-TEC SE 5dr DSG spec page")
    judge.check("nav_tucson_specs",
                navigated_specs(traj, "hyundai", "tucson", "suv-2021",
                                ["16t-150-advance-5dr"]),
                "required: Tucson 1.6T 150 Advance 5d spec page")
    judge.check("answer_kodiaq_boot", entity_number(answer, "kodiaq", 910),
                "Kodiaq luggage space is 910 litres")
    judge.check("answer_tucson_boot", entity_number(answer, "tucson", 620),
                "Tucson luggage space is 620 litres")
    judge.check("answer_bigger", contains_phrase(answer, "kodiaq"),
                "the Kodiaq has the bigger boot")
    judge.check("answer_difference", contains_count(answer, 290),
                "difference is 290 litres")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
