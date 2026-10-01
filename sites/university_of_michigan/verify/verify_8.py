#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--8 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Schools & Colleges (21 total, 19 Ann Arbor); Ross (2 programs, first
    # Business); Stamps (2, Art and Design); SMTD (16, Composition — the
    # most); alice login + save Business; My U-M count.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/schools-colleges\b",
        r"/schools-colleges/ross",
        r"/schools-colleges/stamps",
        r"/schools-colleges/smtd",
        r"/login",
        r"/programs/22\b",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "schools_total", 21)
    check_answer_number(judge, answer, "ann_arbor_count", 19)
    check_answer_number(judge, answer, "ross_programs", 2)
    check_answer_phrase(judge, answer, "ross_first", "Business")
    check_answer_number(judge, answer, "stamps_programs", 2)
    check_answer_phrase(judge, answer, "stamps_first", "Art and Design")
    check_answer_number(judge, answer, "smtd_programs", 16)
    check_answer_phrase(judge, answer, "smtd_first", "Composition")
    check_answer_any(judge, answer, "most_programs_school",
                     ["SMTD", "Music, Theatre & Dance", "School of Music"])
    check_answer_number(judge, answer, "alice_saved_programs", 2)
    check_only_tables_changed(judge, initial, after, {"saved_programs"})
    check_rows_added(judge, initial, after, "saved_programs",
                     [[None, 1, 22, "2026-09-30"]], "saved_program_alice_business")
    check_rows_removed(judge, initial, after, "saved_programs", [],
                     "no_rows_removed_saved_programs")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
