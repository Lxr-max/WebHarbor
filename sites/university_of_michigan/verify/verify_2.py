#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--2 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Winter 2026 (classes begin Jan. 7, MLK Jan. 19); Fall 2026 registration
    # (Backpack opens March 18, undergrad window March 30); Spring/Summer 2026
    # (17 entries); Costs (MI lower-division total $40,194); Financial Aid
    # (r2 fix: the Oct. 1 row now carries the full upstream sentence "Complete
    # the Free Application for Federal Student Aid (FAFSA), as soon as
    # available, ..." so the FAFSA-availability anchor is on the Aid page);
    # carol saved-program count.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/calendars\?term=Winter\+2026",
        r"/calendars\?term=Fall\+2026&type=Registration",
        r"/calendars\?term=Spring",
        r"/admissions/costs",
        r"/admissions/aid",
        r"/login",
        r"/myumich",
    ])
    check_answer_phrase(judge, answer, "w2026_classes_begin", "Jan. 7")
    check_answer_phrase(judge, answer, "w2026_mlk", "Jan. 19")
    check_answer_phrase(judge, answer, "f2026_backpack_opens", "March 18")
    check_answer_phrase(judge, answer, "f2026_reg_window_start", "March 30")
    check_answer_number(judge, answer, "ss2026_reg_entries", 17)
    check_answer_number(judge, answer, "mi_lower_total", 40194)
    check_answer_any(judge, answer, "fafsa_available_date",
                    ["Oct. 1", "October 1", "Oct 1", "oct 1"])
    check_answer_number(judge, answer, "carol_saved_programs", 2)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
