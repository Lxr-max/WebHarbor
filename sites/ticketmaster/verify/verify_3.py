#!/usr/bin/env python3
"""Verify Ticketmaster--3.

My companion uses a wheelchair, so we need accessible seating for Disney Presents The Lion King (Touring) at the Hollywood Pantages Theatre on January 2, 2027. How many accessible options does that performance list, and what are the section, the row, and the all-in price for the two of us together? How much cheaper is that than 2 of the cheapest Standard Admission seats at the same show, and what does the help centre say about how accessible seating is bought?
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

TASK_ID = "Ticketmaster--3"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): accessible seating for Lion King @ Pantages 2027-01-02
# (event 0B00650BD65F6C93): exactly 1 accessible option, Sec ML Row W at
# $23.41 per ticket incl fees (listing 500), $46.82 all-in for 2 together.
# The cheapest Standard Admission at the same show is Sec BALCL Row H at
# $39.90 ($79.80 for 2), so the accessible pair is $32.98 cheaper. The help
# centre's accessible-tickets article: use the Accessible filter on the
# event page or contact the venue's accessibility services.
EVENT_ID = "0B00650BD65F6C93"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "lion king search", r"/search\?q=lion")
    check_visited_path(judge, traj, "the Jan 2 2027 event page", rf"/event/{EVENT_ID}")
    check_visited_path(judge, traj, "the accessible-tickets help article",
                       r"/help/accessible")
    check_answer_number(judge, answer, "accessible option count", 1,
                        ["accessible", "option", "1"])
    check_answer_phrase(judge, answer, "accessible section", "ML")
    check_answer_phrase(judge, answer, "accessible row", "Row W")
    check_answer_money(judge, answer, "all-in price for 2", 46.82)
    check_answer_money(judge, answer, "cheaper than 2 cheapest Standard", 32.98)
    ok_std = ("39.90" in answer) or ("79.80" in answer)
    if ok_std:
        judge.evidence("answer reports the cheapest Standard Admission "
                      "comparison ($39.90 each / $79.80 for 2)")
    else:
        judge.fail("answer does not anchor the comparison to the cheapest "
                   "Standard Admission seats ($39.90 each)")
    ok_buy = ("filter" in answer.lower()
              and ("venue" in answer.lower() or "accessibility services" in answer.lower()))
    if ok_buy:
        judge.evidence("answer reports the help centre's purchase guidance "
                      "(Accessible filter or the venue's accessibility services)")
    else:
        judge.fail("answer does not report the help centre's guidance on how "
                   "accessible seating is bought (Accessible filter on the "
                   "event page or the venue's accessibility services)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
