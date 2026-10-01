#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--10.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Academic calendar Autumn (instruction begins September 22, Preliminary
    # Study List September 22 5 p.m., $200 late fee) -> Winter (January 4) ->
    # dana login -> planner (BIO102, 4 units) -> remove neuroscience ->
    # add MATH51 (planner 1 course, 5 units).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/academic-calendar",
        r"/academic-calendar\?quarter=winter",
        r"/login",
        r"/planner",
        r"/courses\?q=Linear",
        r"/courses/MATH51",
    ])
    check_answer_phrase(judge, answer, "autumn_instruction_begins", "September 22 (Tue)")
    check_answer_phrase(judge, answer, "preliminary_deadline", "September 22 (Tue, 5 p.m.)")
    check_answer_price(judge, answer, "late_fee", "200")
    check_answer_phrase(judge, answer, "winter_first_day", "January 4 (Mon)")
    check_answer_phrase(judge, answer, "dana_planner_courses", "BIO102")
    check_answer_number(judge, answer, "dana_planner_total", 4)
    check_answer_phrase(judge, answer, "dana_final_courses", "MATH51")
    check_answer_number(judge, answer, "dana_final_total", 5)
    check_answer_absent(judge, answer, "dana_bio102_gone", "BIO102, MATH51")
    check_only_tables_changed(judge, initial, after, {"planned_courses"})
    check_rows_changed(judge, initial, after, "planned_courses",
                       [[None, 4, "MATH51", None, None]], "planner_dana_bio102_to_math51")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
