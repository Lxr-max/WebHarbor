#!/usr/bin/env python3
"""Verify Parkers--11.

Publish my owner review of the Volkswagen Golf Hatchback (2020 onwards) on Parkers. My name is Jamie Fletcher; I bought it new in 2023 and rate it 3 out of 5. Describe the infotainment system as frustrating to use while driving but say the car is comfortable on longer trips. Confirm the published review shows my name, rating and purchase details correctly.
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
    entered_identity,
    user_by_email)

TASK_ID = "Parkers--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_owner_reviews",
                navigated_owner_reviews(traj, "volkswagen", "golf", "hatchback-2020"),
                "required: Golf Hatchback (2020 onwards) owner reviews page")
    judge.check("nav_entered_name", entered_identity(traj, "Jamie Fletcher"),
                "required: Jamie Fletcher entered")
    judge.check("answer_confirms_review",
                contains_phrase(answer, "review")
                and contains_phrase(answer, "golf")
                and contains_phrase(answer, "infotainment"),
                "the answer must confirm the Golf review (with the infotainment "
                "mention) appears on the owner reviews page")
    judge.check("answer_states_identity",
                contains_phrase(answer, "jamie fletcher") and contains_count(answer, 3),
                "the answer must restate the review identity: Jamie Fletcher, "
                "rated 3 out of 5")
    # DB after-state: exactly one new owner_reviews row with the required fields
    new = added_rows(after_db, initial_db, "owner_reviews", "id")
    judge.check("one_new_owner_review", len(new) == 1,
                f"expected exactly 1 new owner_reviews row, got {len(new)}")
    if len(new) == 1:
        r = new[0]
        judge.check("review_model", r["make_slug"] == "volkswagen" and r["model_slug"] == "golf"
                    and r["gen_slug"] == "hatchback-2020",
                    f"wrong model: {r['make_slug']}/{r['model_slug']}/{r['gen_slug']}")
        judge.check("review_rating", r["rating"] == 3, f"rating={r['rating']}, expected 3")
        judge.check("review_author", (r["author"] or "").lower() == "jamie fletcher",
                   f"author={r['author']!r}")
        judge.check("review_body_infotainment", "infotainment" in (r["body_json"] or "").lower(),
                   "review body must mention the infotainment system")
        judge.check("review_bought_new_2023",
                   "new" in (r["bought"] or "").lower() and "2023" in (r["bought"] or ""),
                   f"bought={r['bought']!r} must say bought new in 2023")
        judge.check("review_is_not_seed", r["is_seed"] == 0, "submitted review must be is_seed=0")
    judge.check("only_owner_reviews_changed",
                rows_of(after_db, "shortlist_items") == rows_of(initial_db, "shortlist_items")
                and rows_of(after_db, "saved_valuations") == rows_of(initial_db, "saved_valuations")
                and rows_of(after_db, "users") == rows_of(initial_db, "users"),
                "no other table may change")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
