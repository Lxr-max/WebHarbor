#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--18.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_range, check_answer_regex, check_answer_zero_or_phrase,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Stanford University--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Carol login -> saved event (Lunchtime Curator Talk | JANE!, 2026-10-01)
    # -> multifaith search -> Multifaith Dinner save (2) -> remove curator
    # talk (1: Multifaith Dinner) -> seminar search -> first event save ->
    # final count 2.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/saved-events",
        r"/events\?q=multifaith",
        r"/events/53969575639155",
        r"/events\?q=seminar",
    ])
    check_answer_phrase(judge, answer, "carol_saved_events", "Lunchtime Curator Talk")
    check_answer_phrase(judge, answer, "carol_saved_date", "2026-10-01")
    check_answer_phrase(judge, answer, "multifaith_dinner", "Multifaith Dinner")
    check_answer_number(judge, answer, "after_multifaith_count", 2)
    check_answer_number(judge, answer, "after_remove_count", 1)
    check_answer_phrase(judge, answer, "after_remove_titles", "Multifaith Dinner")
    check_answer_number(judge, answer, "final_count", 2)
    check_only_tables_changed(judge, initial, after, {"saved_events"})
    check_rows_removed(judge, initial, after, "saved_events",
                       [[None, 3, 53685756293663, None, None]], "saved_remove_carol_curator")
    # The two saves are the Multifaith Dinner and the first seminar row of
    # /events?q=seminar (eid 53870497268780).
    check_rows_added(judge, initial, after, "saved_events",
                     [[None, 3, 53969575639155, None, None],
                      [None, 3, 53870497268780, None, None]], "saved_add_carol")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
