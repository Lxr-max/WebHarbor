#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--10 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task re-anchored at 4d57185b): the Quick 2 Hire question moves
from industry (empty in this capture — the r1 defect) to the company's
open-job count.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_regex, check_read_only,
    check_only_tables_changed, check_row_matches, check_rows_added,
    check_rows_removed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, run_verifier,
)

TASK_ID = "ZipRecruiter--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "browse", r"/browse$")
    check_visited_path(judge, traj, "letter_r", r"/browse/titles/R")
    check_visited_path(judge, traj, "rn_title", r"/Jobs/registered-nurse$")
    check_visited_path(judge, traj, "salary", r"/Salaries/registered-nurse-Salary")
    check_visited_path(judge, traj, "nearby", r"/Job/Registered-Nurse-Stepdown")
    check_visited_path(judge, traj, "company", r"/co/Quick-2-Hire")
    check_visited_path(judge, traj, "serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    # -- answer ground truth --
    check_answer_number(judge, answer, "roles", 74)
    check_answer_number(judge, answer, "avg", "92,525")
    check_answer_number(judge, answer, "avg_hour", "44.48")
    check_answer_number(judge, answer, "median", "92,525")
    check_answer_phrase(judge, answer, "nearby_title", "Registered Nurse Stepdown")
    check_answer_phrase(judge, answer, "nearby_co", "Quick 2 Hire")
    check_answer_phrase(judge, answer, "nearby_loc", "On-site")
    check_answer_phrase(judge, answer, "nearby_pay", "$47 - $50/hr")
    check_answer_number(judge, answer, "co_open", 1)
    check_answer_phrase(judge, answer, "city1", "San Mateo County, CA")
    check_answer_number(judge, answer, "city1_avg", "129,338")
    check_answer_phrase(judge, answer, "city2", "Mineral, VA")
    check_answer_number(judge, answer, "city2_avg", "127,705")
    check_answer_phrase(judge, answer, "city3", "Portola Valley, CA")
    check_answer_number(judge, answer, "city3_avg", "122,470")
    check_answer_phrase(judge, answer, "related", "Manager Interventional Radiology Rn")
    check_answer_number(judge, answer, "related_avg", "147,291")
    check_answer_number(judge, answer, "rn_ny", 24)
    check_answer_number(judge, answer, "rn_ny_quick", 9)
    check_answer_phrase(judge, answer, "quick_first_co", "Park Ave Gastroenterology")
    check_answer_phrase(judge, answer, "quick_first_pay", "$40 - $50/hr")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
