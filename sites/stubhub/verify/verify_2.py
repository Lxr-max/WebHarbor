#!/usr/bin/env python3
"""Verify StubHub--2.

Metallica plays the same Las Vegas venue in early October. Compare the two-day pass covering October 1 and 3 against the October 1 and October 3 single-night events: report each event's total listing count, get-in price, and the section of its cheapest listing. Compute the pass's implied cost per night. Report the venue's full name and city, and state whether the pass or the two single nights together are the cheaper way to see both shows.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--2"

import re


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_pass_event", r"/metallica-las-vegas-tickets-10-1-2026/event/160572545")
    check_visited_path(judge, traj, "visited_oct1_single", r"/metallica-las-vegas-tickets-10-1-2026/event/160569378")
    check_visited_path(judge, traj, "visited_oct3_single", r"/metallica-las-vegas-tickets-10-3-2026/event/160569380")
    
    check_answer_number(judge, answer, "pass_listing_count", 29)
    check_answer_number(judge, answer, "pass_getin", 1137)
    check_answer_phrase(judge, answer, "pass_cheapest_section", "310")
    check_answer_number(judge, answer, "oct1_listing_count", 26)
    check_answer_number(judge, answer, "oct1_getin", 749)
    check_answer_phrase(judge, answer, "oct1_cheapest_section", "407")
    check_answer_number(judge, answer, "oct3_listing_count", 10)
    check_answer_number(judge, answer, "oct3_getin", 1124)
    check_answer_phrase(judge, answer, "oct3_cheapest_section", "110")
    check_answer_phrase(judge, answer, "venue_name", "Sphere")
    check_answer_phrase(judge, answer, "venue_city", "Las Vegas")
    judge.check("per_night_computed",
                bool(re.search(r"(?<![\d.])568\.50?(?![\d.])", answer)),
                "answer must compute the pass's implied cost per night ($568.50)")
    judge.check("pass_vs_singles_verdict",
                "pass" in answer.casefold() and re.search(r"cheaper", answer.casefold()),
                "answer must state the two-day pass is the cheaper way to see both shows")
    from comparison_checks import entity_numbers
    labels = [r"two[- ]day pass|two[- ]night pass", r"Oct(?:ober)?[ .]*1(?:st)? single", r"Oct(?:ober)?[ .]*3(?:rd)? single"]
    for i, values in enumerate([(29, 1137, 310), (26, 749, 407), (10, 1124, 110)]):
        entity_numbers(judge, answer, "event_values_"+str(i), [labels[i]], labels[:i]+labels[i+1:], values)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
