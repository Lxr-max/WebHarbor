#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--13.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Bob login -> planner (ECON1 5, PSYCH1 5, total 10) -> remove PSYCH1 ->
    # add BIO102 (2 courses, 9) -> remove ECON1 -> add PHYSICS41 ->
    # final planner [BIO102, PHYSICS41], 8 units.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/planner",
        r"/courses\?q=Introduction",
        r"/courses/BIO102",
        r"/courses\?q=Mechanics",
        r"/courses/PHYSICS41",
    ])
    check_answer_phrase(judge, answer, "bob_planner_econ1", "ECON1")
    check_answer_phrase(judge, answer, "bob_planner_psych1", "PSYCH1")
    check_answer_number(judge, answer, "bob_total_units", 10)
    check_answer_number(judge, answer, "after_neuro_count", 2)
    check_answer_number(judge, answer, "after_neuro_total", 9)
    check_answer_phrase(judge, answer, "bob_final_bio102", "BIO102")
    check_answer_phrase(judge, answer, "bob_final_physics41", "PHYSICS41")
    check_answer_number(judge, answer, "bob_final_total", 8)
    check_answer_absent(judge, answer, "econ1_gone", "ECON1, BIO102")
    check_answer_absent(judge, answer, "psych1_gone", "PSYCH1, BIO102")
    check_only_tables_changed(judge, initial, after, {"planned_courses"})
    check_rows_removed(judge, initial, after, "planned_courses",
                       [[None, 2, "ECON1", None, None],
                        [None, 2, "PSYCH1", None, None]], "planner_bob_removals")
    check_rows_added(judge, initial, after, "planned_courses",
                     [[None, 2, "BIO102", None, None],
                      [None, 2, "PHYSICS41", None, None]], "planner_bob_additions")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
