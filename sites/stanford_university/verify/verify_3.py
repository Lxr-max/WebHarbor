#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--3.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Fei-Fei Li search (Sequoia Capital Professor title) -> profile (CS dept,
    # research interests) -> Mathematics dept (58, first Mohammed Abouzaid,
    # Professor of Mathematics) -> ADL leader Juan Alonso (the bio-covering
    # search hits uniquely; the AA roster is an equivalent route) ->
    # Psychology count (54).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/faculty\?q=Fei-Fei",
        r"dept=Mathematics",
        r"dept=Psychology",
    ])
    check_answer_phrase(judge, answer, "feifei_title", "Sequoia Capital Professor")
    check_answer_phrase(judge, answer, "feifei_dept", "Computer Science")
    check_answer_any(judge, answer, "feifei_interest",
                    ["machine learning", "computer vision", "robotics", "human vision", "ai+healthcare"])
    check_answer_number(judge, answer, "math_faculty_count", 58)
    check_answer_phrase(judge, answer, "math_first_name", "Mohammed Abouzaid")
    check_answer_phrase(judge, answer, "math_first_title", "Professor of Mathematics")
    check_visited_any(judge, traj, "adl_route", [r"q=Aerospace", r"dept=Aeronautics"])
    check_answer_number(judge, answer, "adl_search_results", 1)
    check_answer_phrase(judge, answer, "adl_leader", "Juan Alonso")
    check_answer_regex(judge, answer, "adl_leader_title", r"Coffman Professor")
    check_answer_number(judge, answer, "psych_faculty_count", 54)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
