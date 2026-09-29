#!/usr/bin/env python3
"""Verify Ticketmaster--2.

I have a Citi credit card and want early access to Disney Presents The Lion King (Touring) at the Hollywood Pantages Theatre on January 2, 2027. For that date, when does the Citi cardmember presale open and close, and what exactly do I need to enter during checkout to buy with it? Which presale runs right after the Citi window? Can I use a Citi presale for the theatre's other January dates instead - check what presales those dates list. Also, how many tickets can one order contain, and does the help centre say presale access guarantees tickets?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_money,
                        check_answer_number, check_answer_phrase,
                        check_input_action, check_only_tables_changed,
                        check_purchase_order, check_read_only,
                        check_row_added, check_row_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Ticketmaster--2"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Lion King @ Hollywood Pantages 2027-01-02 (event
# 0B00650BD65F6C93). Citi(R) Cardmember Presale runs 2026-10-25 to
# 2026-10-29; checkout needs the first 6 digits of the eligible Citi card
# as the presale code plus payment with the Citi card. The VIP Package
# Presale follows (2026-10-30 to 2026-11-03). The other January dates list
# Venue Presales (Jan 9 = 0B00650BD68B6CD2, Jan 10 = 0B00650BD6966CD7), an
# Artist Fan Club Presale (Jan 17 = 0B00650BD6C06D07) and no presale at all
# (Jan 3 = 0B00650BD66A6C9B, Jan 16 = 0B00650BD6B66CFE) - so no Citi presale
# for those dates. Event ticket limit: 8. Help centre presale article:
# "Presale tickets are limited and not guaranteed."
EVENT_ID = "0B00650BD65F6C93"
OTHER_JANUARY = ("0B00650BD68B6CD2", "0B00650BD6966CD7", "0B00650BD6C06D07",
                 "0B00650BD66A6C9B", "0B00650BD6B66CFE")


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "lion king search", r"/search\?q=lion")
    check_visited_path(judge, traj, "the Jan 2 2027 event page", rf"/event/{EVENT_ID}")
    seen_other = [e for e in OTHER_JANUARY
                  if any(rf"/event/{e}" in u for u in
                         [s.get("url", "") for s in traj.get("steps", [])]
                         + [traj.get("final_url", "")])]
    if len(seen_other) >= 2:
        judge.evidence(f"checked the other January dates: {seen_other}")
    else:
        judge.fail("never opened the theatre's other January dates to check "
                   "their presales (need at least two of "
                   f"{OTHER_JANUARY})")
    check_visited_path(judge, traj, "the presale help article", r"/help/presale")
    check_answer_any(judge, answer, "Citi presale open date",
                     ["2026-10-25", "October 25", "Oct 25", "10-25", "10/25"])
    check_answer_any(judge, answer, "Citi presale close date",
                     ["2026-10-29", "October 29", "Oct 29", "10-29", "10/29"])
    check_answer_phrase(judge, answer, "presale code to enter", "first 6 digits")
    check_answer_phrase(judge, answer, "payment method requirement", "Citi")
    if "VIP" in answer:
        judge.evidence("answer names the VIP Package Presale as the one right "
                      "after the Citi window")
    else:
        judge.fail("answer does not name which presale runs right after the "
                   "Citi window (VIP Package Presale)")
    if ("Jan 9" in answer or "Jan 10" in answer or "January 9" in answer
            or "January 10" in answer or "9" in answer and "10" in answer):
        judge.evidence("answer reports what presales the other January dates list")
    else:
        judge.fail("answer does not report the other January dates' presales "
                   "(Venue Presales on Jan 9/10, Artist Fan Club on Jan 17, "
                   "none on Jan 3/16)")
    check_answer_number(judge, answer, "per-order ticket limit", 8,
                        ["limit", "order", "8"])
    if "not guaranteed" in answer.lower():
        judge.evidence("answer reports the help centre's guarantee wording "
                      "(presale tickets are limited and not guaranteed)")
    else:
        judge.fail("answer does not state that the help centre says presale "
                   "access does not guarantee tickets")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
