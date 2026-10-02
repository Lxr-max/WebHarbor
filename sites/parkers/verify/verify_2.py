#!/usr/bin/env python3
"""Verify Parkers--2.

I'm deciding whether to sell my BMW 318d M Sport privately or trade it in. Use Parkers' valuation for the 2023/73-plate car to report the private-sale and part-exchange ranges, calculate their midpoints, and explain which route suggests a higher return and by how much.
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
    navigated_to_path, navigated_reg_lookup, navigated_review, navigated_review_section,
    navigated_shortlist, navigated_sign_in, navigated_site_search,
    navigated_specs, navigated_specs_gen, navigated_valuation_chain,
    run_verifier, shortlist_listing_ids, added_rows, removed_rows, rows_of,
    user_by_email)

TASK_ID = "Parkers--2"

import re as _re


def _route_verdict(answer):
    """Which route does the answer's verdict sentence credit?

    Finds verdict phrases (earns more / better / wins / beats / higher) and
    checks which route (private vs dealer/part-ex) is mentioned closest
    before the verdict, without crossing a sentence boundary.
    """
    text = (answer or "").lower()
    for m in _re.finditer(r"earns? more|is better|better route|wins|beats|"
                          r"higher|more money|more for me|suggests? £?[\d,]+ more", text):
        window = text[max(0, m.start() - 110):m.start()]
        window = window.rsplit(".", 1)[-1]
        priv = dm = None
        for mm in _re.finditer(r"privat\w*|dealer|part[- ]ex\w*|trading it in|"
                               r"trade[- ]?in", window):
            if mm.group(0).startswith("privat"):
                priv = mm.start()
            else:
                dm = mm.start()
        if priv is not None and (dm is None or priv >= dm):
            return "private"
        if dm is not None and priv is None:
            return "dealer"
    return None


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    judge.check("nav_valuation_chain",
                navigated_valuation_chain(traj, "bmw", "3-series", "saloon-2019",
                                          "318d-m-sport-4d", "2023/73", deriv_id=70),
                "required: 3-series saloon-2019 valuation chain for 318d M Sport 4d 2023/73")
    judge.check("answer_private_range", labeled_range(answer, "private", 13540, 17960),
                "private range must quote £13,540 and £17,960")
    judge.check("answer_part_ex", labeled_range(answer, "part", 14650, 16060),
                "part-exchange value must quote £14,650 and £16,060")
    # The task now names the two routes (private sale vs part-exchange), so the
    # mid-point comparison is unambiguous: private mid 15,750 > part-ex mid 15,355.
    # The verdict direction is checked (the route credited with earning more).
    judge.check("answer_route", _route_verdict(answer) == "private",
                "the mid-points favour selling privately (not the dealer route)")
    judge.check("answer_midpoints_and_difference", contains_amount(answer, 15750) and contains_amount(answer, 15355) and contains_amount(answer, 395), "Private midpoint £15,750; part-exchange midpoint £15,355; advantage £395")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
