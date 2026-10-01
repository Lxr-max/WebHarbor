#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--6 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_only_tables_changed,
    check_screenshots, check_seed_contract, check_trajectory_identity,
    check_visited_all, check_visited_any, check_visited_path, final_answer,
    run_verifier,
)

TASK_ID = "University of Michigan--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Carol login; Workshop / Seminar (15); meditat search (Heartfulness
    # Meditation + Learn to Meditate in 3 days); Heartfulness (Virtual, ITS)
    # saved; genomics (9); Carol totals (2 events, 1 backpack class).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/events\?[^ ]*type=Workshop",
        r"/events\?q=meditat",
        r"/events/143758",
        r"/library\?q=genomics",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "workshop_count", 15)
    check_answer_count_at_least(judge, answer, "meditation_events",
                                 ["Heartfulness Meditation",
                                  "Learn to Meditate in 3 days"], 2)
    check_answer_phrase(judge, answer, "heartfulness_location", "Virtual")
    check_answer_phrase(judge, answer, "heartfulness_sponsor", "Information and Technology Services")
    check_answer_number(judge, answer, "genomics_count", 9)
    check_answer_number(judge, answer, "carol_saved_events", 2)
    check_answer_number(judge, answer, "carol_backpack", 1)
    check_only_tables_changed(judge, initial, after, {"saved_events"})
    check_rows_added(judge, initial, after, "saved_events",
                     [[None, 3, 19, "2026-09-30"]], "saved_event_carol_heartfulness")
    check_rows_removed(judge, initial, after, "saved_events", [],
                     "no_rows_removed_saved_events")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
