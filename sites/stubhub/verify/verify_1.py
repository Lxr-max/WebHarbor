#!/usr/bin/env python3
"""Verify StubHub--1.

For the October 4 Chargers at Seahawks game, find listings for a party of 4 with a clear view under $400 per ticket. Report how many listings match all three conditions and the cheapest match's section, row, and per-ticket price. Separately, report the cheapest 4-ticket listing in the 300 Level zone, and state which of the two options costs less for four tickets.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--1"

import re


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_chargers_event", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504")
    check_visited_path(judge, traj, "applied_qty4_price400_clearview", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504\?quantity=4&price_max=400&sort=price&features=Clear\+view|features=Clear\+view[^ ]*quantity=4|quantity=4[^ ]*features=Clear")
    check_visited_path(judge, traj, "applied_zone_300", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504\?[^ ]*zone=300\+Level")
    
    check_answer_number(judge, answer, "matching_listing_count", 5)
    check_answer_phrase(judge, answer, "cheapest_match_section", "Upper 300-Level")
    check_answer_number(judge, answer, "cheapest_match_price", 265)
    check_answer_phrase(judge, answer, "zone_cheapest_section", "307")
    check_answer_phrase(judge, answer, "zone_cheapest_row", "II")
    check_answer_number(judge, answer, "zone_cheapest_price", 324)
    judge.check("cheaper_option_for_four",
                "clear" in answer.casefold() and "1060" in re.sub(r"[\$,]", "", answer),
                "answer must state the clear-view match is cheaper for four tickets ($1,060 vs $1,296)")
    check_answer_number(judge, answer, "four_ticket_cheaper_total", 1060)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
