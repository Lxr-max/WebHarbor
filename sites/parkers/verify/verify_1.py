#!/usr/bin/env python3
"""Verify Parkers--1.

My aunt is selling her Vauxhall Corsa, registration BX73TGH. Help her put the asking prices she sees in context: value her car through Parkers' registration lookup and report the exact version, private-sale range and dealer range. Compare those figures with the cheapest Corsa currently advertised, making clear that the listing may be a different age or version rather than a like-for-like valuation.
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

TASK_ID = "Parkers--1"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_reg_lookup", navigated_reg_lookup(traj, "BX73TGH"),
                "required: registration search for BX73TGH")
    # the registration flow goes straight to select-a-valuation, so the
    # used-prices chain is replaced by the reg -> select -> free requirement
    judge.check("nav_valuation_pages",
                navigated_to_path(traj, "/vauxhall/corsa/hatchback-2020/12-design-5dr/9548/select-a-valuation")
                and navigated_to_path(traj, "/vauxhall/corsa/hatchback-2020/12-design-5dr/9548/free-valuation"),
                "required: select-a-valuation and free-valuation pages for the "
                "BX73TGH Corsa 1.2 Design 5dr 2023/73")
    judge.check("nav_corsa_listings",
                navigated_c4s_search(traj, make="vauxhall", model="corsa")
                or navigated_c4s_search(traj, make="vauxhall"),
                "required: cars-for-sale search scoped to Vauxhall (Corsa)")
    judge.check("answer_version", contains_phrase(answer, "1.2 design 5dr"),
                "the exact version must be named: 1.2 Design 5dr")
    judge.check("answer_private_range", labeled_range(answer, "private", 7010, 9290),
                "private range must quote £7,010 and £9,290")
    judge.check("answer_dealer_range", labeled_range(answer, "dealer", 9880, 10500),
                "dealer range must quote £9,880 and £10,500")
    judge.check("answer_cheapest_corsa", contains_amount(answer, 5995),
                "cheapest Corsa listing is £5,995 (2015/15)")
    judge.check("answer_position", contains_phrase(answer, "below"),
                "£5,995 sits below the £9,880-£10,500 dealer range")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
