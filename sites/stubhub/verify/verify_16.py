#!/usr/bin/env python3
"""Verify StubHub--16.

On the October 4 Chargers at Seahawks event page, sort listings by Best deal. Report the three listings with the largest discounts: their sections, current prices, and original prices. Compute each saving in dollars and as a percentage of the original price. Which section offers the biggest discount, and how many total listings does the event have?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--16"

import re


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_chargers_event", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504")
    check_visited_path(judge, traj, "best_deal_sort", r"/event/160436504\?[^ ]*sort=best_deal")
    
    for section, cur, was, save, pct in (("239", 449, 659, 210, 32),
                                         ("CLB212", 485, 687, 202, 29),
                                         ("337", 244, 409, 165, 40)):
        check_answer_phrase(judge, answer, f"section_{section}", section)
        check_answer_number(judge, answer, f"current_{section}", cur)
        check_answer_number(judge, answer, f"original_{section}", was)
        check_answer_number(judge, answer, f"saving_{section}", save)
        judge.check(f"percent_{section}",
                    re.search(rf"{pct}%", answer) is not None,
                    f"answer must compute the {section} saving as {pct}%")
    judge.check("biggest_discount_section", "239" in answer,
                "answer must name section 239 as the biggest discount")
    check_answer_number(judge, answer, "total_listings", 30)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
