#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--7.

Instant Cash Offer: value a 2018 Honda Civic EX 4-door hatchback with 60,000
miles, ZIP 98101, blue exterior, one key, original owner, no payments
remaining; then a 2019 Toyota RAV4 XLE with 55,000 miles the same way; state
which car is worth more. Read-only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_all, contains_any,
                        check_trajectory_identity, check_read_only)

TASK_ID = "Cars.com--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_read_only(judge, initial_db, after_db)

    judge.check("nav_offer_start", navigated_to(traj, "/sell/instant-offer/"),
                "required: the Instant Cash Offer start page")
    judge.check("nav_offer_details", navigated_to(traj, "/sell/instant-offer/details/"),
                "required: the offer details step (both flows)")
    judge.check("nav_offer_result", navigated_to(traj, "/sell/instant-offer/offer/"),
                "required: the offer result page (both flows)")

    # Civic flow: initial estimate $10,650 - $13,050 right after picking the
    # vehicle; final offer $10,525 - $12,925 after the details
    judge.check("answer_civic_initial",
                contains_int(answer, 10650) and contains_int(answer, 13050),
                "expected the Civic initial estimate $10,650 - $13,050")
    judge.check("answer_civic_final",
                contains_int(answer, 10525) and contains_int(answer, 12925),
                "expected the Civic final offer $10,525 - $12,925")

    # RAV4 flow: final offer $15,275 - $17,875
    judge.check("answer_rav4_final",
                contains_int(answer, 15275) and contains_int(answer, 17875),
                "expected the RAV4 final offer $15,275 - $17,875")

    # which is worth more: the RAV4
    judge.check("answer_worth_more",
                contains_all(answer, ["RAV4"]) and contains_any(answer, ["worth more", "more", "higher"]),
                "expected: the RAV4 is worth more")
    judge.check("answer_mentions_civic", contains_all(answer, ["Civic"]),
                "expected the Civic flow to be reported")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
