#!/usr/bin/env python3
"""Verify StubHub--14.

For the October 11 49ers at Seahawks game, compare ticket zones. Report the lowest-priced listing in the 100 Level, 200 Level, and 300 Level zones with section and row for each. State which zone has the cheapest get-in price and the price gap between the cheapest and most expensive zone, and report how many total listings the event has across all zones.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--14"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_49ers_event", r"/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498")
    check_visited_path(judge, traj, "zone_100_filter", r"/event/160436498\?[^ ]*zone=100\+Level")
    check_visited_path(judge, traj, "zone_200_filter", r"/event/160436498\?[^ ]*zone=200\+Level")
    check_visited_path(judge, traj, "zone_300_filter", r"/event/160436498\?[^ ]*zone=300\+Level")
    
    check_answer_phrase(judge, answer, "zone100_section", "150")
    check_answer_number(judge, answer, "zone100_price", 477)
    check_answer_phrase(judge, answer, "zone200_section", "215")
    check_answer_number(judge, answer, "zone200_price", 645)
    check_answer_phrase(judge, answer, "zone300_section", "302")
    check_answer_number(judge, answer, "zone300_price", 367)
    judge.check("cheapest_zone_verdict", "300" in answer and "cheapest" in answer.casefold(),
                "answer must state the 300 Level has the cheapest get-in")
    check_answer_number(judge, answer, "zone_gap", 278)
    check_answer_number(judge, answer, "total_listings", 28)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
