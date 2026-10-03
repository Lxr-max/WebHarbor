#!/usr/bin/env python3
"""Verify Ticketmaster--12.

I'm planning a big group outing of 12 to Aladdin - The Musical at the New Amsterdam Theatre in New York, and the same group might also catch a New York Knicks game at Madison Square Garden. How many tickets can a single order contain for each show? What does the help centre say happens to orders that exceed the published ticket limit, and which personal details does it say are checked when enforcing limits? Does the Terms of Use add anything about how limits are enforced?
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

TASK_ID = "Ticketmaster--12"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Aladdin - The Musical @ New Amsterdam Theatre event pages
# show "Event ticket limit: 8."; New York Knicks @ Madison Square Garden
# event pages show "Event ticket limit: 12." (so the 12-person group fits a
# single Knicks order but exceeds the Aladdin limit). Help centre
# ticket-limits article: orders that exceed the published limit may be
# cancelled without notice, including orders associated with the same
# name, e-mail address, billing address, or credit card number. Terms of
# Use (/legal/terms): "Ticket limits are enforced per event and per
# household; orders that exceed published limits may be cancelled without
# notice."
ALADDIN_EVENT_PREFIX = "030064AEEB4"   # every Aladdin @ New Amsterdam event id shares it
KNICKS_EVENT_PREFIX = "3B006511E9"   # every Knicks @ MSG event id shares it


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "aladdin search", r"/search\?q=aladdin")
    check_visited_path(judge, traj, "an Aladdin New Amsterdam event page",
                       rf"/event/{ALADDIN_EVENT_PREFIX}")
    check_visited_path(judge, traj, "a Knicks MSG event page",
                       rf"/event/{KNICKS_EVENT_PREFIX}")
    check_visited_path(judge, traj, "ticket-limits help article", r"/help/ticket-limits")
    check_visited_path(judge, traj, "the Terms of Use page", r"/legal/terms")
    check_answer_number(judge, answer, "Aladdin ticket limit", 8,
                        ["aladdin", "8"])
    check_answer_number(judge, answer, "Knicks ticket limit", 12,
                        ["knicks", "12"])
    check_answer_any(judge, answer, "consequence of exceeding",
                     ["cancelled without notice", "cancelled", "canceled"])
    ok_details = ("name" in answer.lower() and "e-mail" in answer.lower()
                  and "billing" in answer.lower() and "credit card" in answer.lower())
    if ok_details:
        judge.evidence("answer lists the personal details checked when "
                      "enforcing limits (name, e-mail, billing address, "
                      "credit card number)")
    else:
        judge.fail("answer does not list the personal details the help centre "
                   "says are checked (name, e-mail address, billing address, "
                   "credit card number)")
    ok_terms = ("per event" in answer.lower() and "household" in answer.lower())
    if ok_terms:
        judge.evidence("answer reports the Terms of Use clause (limits "
                      "enforced per event and per household)")
    else:
        judge.fail("answer does not report what the Terms of Use add about "
                   "how limits are enforced (per event and per household)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
