#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--12 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review, seed md5
3f5e930aa820d1b62309ec3feeb4536b, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Fall 2026 Academic (classes begin Aug. 31; Thanksgiving Nov. 25-27;
    # Commencement Dec. 20); Registration (Backpack opens March 18); Winter
    # 2027 Academic (9 entries, classes begin Jan. 13); Apply plans (ED Nov.
    # 1 binding, decision By Dec. 24; RD Feb. 1); bob backpack count.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/calendars\?term=Fall\+2026&type=Academic",
        r"/calendars\?term=Fall\+2026&type=Registration",
        r"/calendars\?term=Winter\+2027[^ ]*type=Academic",
        r"/admissions/apply",
        r"/login",
        r"/myumich",
    ])
    check_answer_phrase(judge, answer, "f2026_classes_begin", "Aug. 31")
    check_answer_phrase(judge, answer, "f2026_thanksgiving_from", "Nov. 25")
    check_answer_phrase(judge, answer, "f2026_thanksgiving_to", "Nov. 27")
    check_answer_phrase(judge, answer, "f2026_commencement", "Dec. 20")
    check_answer_phrase(judge, answer, "f2026_backpack_opens", "March 18")
    check_answer_number(judge, answer, "w2027_entries", 9)
    check_answer_phrase(judge, answer, "w2027_classes_begin", "Jan. 13")
    check_answer_phrase(judge, answer, "ed_deadline", "Nov. 1")
    check_answer_phrase(judge, answer, "ed_decision", "Dec. 24")
    check_answer_phrase(judge, answer, "rd_deadline", "Feb. 1")
    check_answer_regex(judge, answer, "binding_plan",
                      r"early decision[^.;]{0,40}binding|binding[^.;]{0,40}early decision")
    check_answer_number(judge, answer, "bob_backpack_total", 2)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
