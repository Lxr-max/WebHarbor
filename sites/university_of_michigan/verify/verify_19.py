#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--19 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Fall 2025 (classes begin Aug. 25, study break Oct. 13-14); Winter 2026
    # (Jan. 7); Winter 2027 (9 academic entries, classes begin Jan. 13);
    # Costs (MI upper-division tuition & fees $21,268; nonresident
    # lower-division total $88,394); alice login; Alice's first Backpack
    # class detail page (CHEM 125 — Gen Chem Lab I, Alexander Stark) opened
    # from My U-M; saved-event count (1: T.REX).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/calendars\?term=Fall\+2025",
        r"/calendars\?term=Winter\+2026",
        r"/calendars\?term=Winter\+2027",
        r"/admissions/costs",
        r"/login",
        r"/myumich",
        r"/courses/class/10699",
    ])
    check_answer_phrase(judge, answer, "f2025_classes_begin", "Aug. 25")
    check_answer_phrase(judge, answer, "f2025_study_break_from", "Oct. 13")
    check_answer_phrase(judge, answer, "f2025_study_break_to", "Oct. 14")
    check_answer_phrase(judge, answer, "w2026_classes_begin", "Jan. 7")
    check_answer_number(judge, answer, "w2027_academic_entries", 9)
    check_answer_phrase(judge, answer, "w2027_classes_begin", "Jan. 13")
    check_answer_number(judge, answer, "mi_upper_tuition", 21268)
    check_answer_number(judge, answer, "nonres_lower_total", 88394)
    check_answer_phrase(judge, answer, "alice_first_backpack_course", "CHEM 125")
    check_answer_phrase(judge, answer, "alice_first_backpack_instructor", "Alexander Stark")
    check_answer_number(judge, answer, "alice_saved_events", 1)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
