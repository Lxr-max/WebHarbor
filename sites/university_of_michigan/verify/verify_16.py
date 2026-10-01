#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--16 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Courses 'data' (32); STATS subject (STATS 250 'Intr Stat&Data Anlys',
    # 66 sections; first section 13492, Alicia Romero); psychology (9);
    # dana login; r2 re-anchor: the STATS 250 first section (class 13492 —
    # outside Dana's seeded Backpack) is added and then removed again, so
    # the honest end state is row-identical to the seed (a single toggle, a
    # wrong section or an un-removed add all leave a backpack_items delta
    # and FAIL here). Reported remainder: 1 class.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/courses\?q=data",
        r"/courses/subject/STATS",
        r"/courses/class/13492",
        r"/courses\?q=psychology",
        r"/login",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "data_courses", 32)
    check_answer_phrase(judge, answer, "stats250_title", "Intr Stat&Data Anlys")
    check_answer_number(judge, answer, "stats250_sections", 66)
    check_answer_number(judge, answer, "stats250_first_nbr", 13492)
    check_answer_phrase(judge, answer, "stats250_first_instructor", "Alicia Romero")
    check_answer_number(judge, answer, "psychology_courses", 9)
    check_answer_number(judge, answer, "dana_backpack_total", 1)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
