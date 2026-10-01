#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--2.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # EE + Graduate + Winter (career filter matches exactly) -> 6 courses,
    # first by code EE214B "Advanced Integrated Circuit Design" (3 units) ->
    # CS106A WAYS FR + ROP -> Mathematics + FR -> 28 matches.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"subject=EE&career=Graduate&term=Winter",
        r"/courses/CS106A",
        r"subject=MATH",
        r"ways=Formal",
    ])
    check_answer_number(judge, answer, "ee_grad_winter_count", 6)
    check_answer_number_absent(judge, answer, "ee_count_trip_12", 12)
    check_answer_phrase(judge, answer, "ee_first_code", "EE214B")
    check_answer_phrase(judge, answer, "ee_first_title", "Advanced Integrated Circuit Design")
    check_answer_phrase(judge, answer, "cs106a_ways", "Formal Reasoning (FR)")
    check_answer_phrase(judge, answer, "cs106a_grading", "ROP - Letter or Credit/No Credit")
    check_answer_number(judge, answer, "math_fr_count", 28)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
