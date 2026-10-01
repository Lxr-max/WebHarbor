#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--9 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # a-f tab (60); r2 disambiguation: clear the tab back to a-z before the
    # bio search (unique 15); BCN program (College of Literature, Science,
    # and the Arts (LSA), 100 programs via the now-working program->school
    # link); psychology search (2); carol login + save BCN; My U-M count.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/programs\?[^ ]*letter=a-f",
        r"/programs\?q=bio",
        r"/programs/21\b",
        r"/schools-colleges/lsa",
        r"/programs\?q=psychology",
        r"/login",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "af_count", 60)
    check_answer_number(judge, answer, "bio_count", 15)
    check_answer_phrase(judge, answer, "bcn_school",
                        "College of Literature, Science, and the Arts")
    check_answer_number(judge, answer, "lsa_program_count", 100)
    check_answer_number(judge, answer, "psychology_count", 2)
    check_answer_number(judge, answer, "carol_saved_programs", 3)
    check_only_tables_changed(judge, initial, after, {"saved_programs"})
    check_rows_added(judge, initial, after, "saved_programs",
                     [[None, 3, 21, "2026-09-30"]], "saved_program_carol_bcn")
    check_rows_removed(judge, initial, after, "saved_programs", [],
                     "no_rows_removed_saved_programs")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
