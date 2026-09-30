#!/usr/bin/env python3
"""Verify Ticketmaster--16.

I can only pick one winter show and want the crowd's verdict on Trans-Siberian Orchestra. What is their average fan rating, how many reviews is it based on, and how many of their events are listed for December 2026? When and at which venue is their first December show? For comparison, what is Wicked (Touring)'s average rating and review count, how many of its events are listed in 2026, and which act do fans rate higher?
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

TASK_ID = "Ticketmaster--16"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): Trans-Siberian Orchestra artist page (780815): average fan
# rating 4.6 out of 5 based on 1617 reviews; 18 of its events are listed
# for December 2026; the first December show is Wed, Dec 02, 2026 at
# Bridgestone Arena (Nashville). Wicked (Touring) artist page (864373):
# rating 4.7 from 936 reviews; its 20 tour stops run Mar 31, 2027 through
# Apr 18, 2027, so 0 events are listed in 2026. Fans rate Wicked (Touring)
# higher (4.7 > 4.6).
TSO_ID = "780815"
WICKED_ID = "864373"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "TSO search", r"/search\?q=")
    check_visited_path(judge, traj, "the TSO artist page", rf"/artist/{TSO_ID}")
    check_visited_path(judge, traj, "the Wicked artist page", rf"/artist/{WICKED_ID}")
    check_answer_number(judge, answer, "TSO average fan rating", 4.6,
                        ["4.6", "rating"])
    check_answer_number(judge, answer, "TSO review count", 1617,
                        ["1617", "review"])
    check_answer_number(judge, answer, "TSO December 2026 events", 18,
                        ["december", "dec", "18"])
    check_answer_any(judge, answer, "first December show date",
                     ["Dec 02", "Dec 2", "December 2", "12-02", "12/02"])
    check_answer_phrase(judge, answer, "first December show venue", "Bridgestone")
    check_answer_number(judge, answer, "Wicked average rating", 4.7,
                        ["4.7", "rating"])
    check_answer_number(judge, answer, "Wicked review count", 936,
                        ["936", "review"])
    ok_2026 = ("0" in answer) and ("2026" in answer)
    if ok_2026:
        judge.evidence("answer reports Wicked (Touring) has 0 events listed in 2026")
    else:
        judge.fail("answer does not report how many Wicked (Touring) events "
                   "are listed in 2026 (0)")
    import re as _re
    higher_sents = [s for s in _re.findall(r"[^.]*higher[^.]*\.", answer)
                    or _re.findall(r"[^.]*higher[^.]*$", answer)]
    ok_higher = (higher_sents
                 and all("wicked" in s.lower() for s in higher_sents)
                 and not any("trans-siberian" in s.lower() and "wicked" not in s.lower()
                             for s in higher_sents))
    if ok_higher:
        judge.evidence("answer says fans rate Wicked (Touring) higher (4.7 > 4.6)")
    else:
        judge.fail("answer does not say which act fans rate higher "
                   "(Wicked (Touring), 4.7 vs 4.6) — or credits the higher "
                   "rating to the wrong act")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
