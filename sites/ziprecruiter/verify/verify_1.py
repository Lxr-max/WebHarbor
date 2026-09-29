#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--1 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): adds the second filtered listing's
company profile (BAYADA Home Health Care: industry, size, headquarters).
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York")
    check_visited_path(judge, traj, "quick_filter", r"apply=quick")
    check_visited_path(judge, traj, "days5_filter", r"days=5")
    check_visited_path(judge, traj, "job_detail", r"/Job/Registered-Nurse-Gastroenterology.*jid=")
    check_visited_path(judge, traj, "second_detail", r"/Job/Private-Duty-Registered-Nurse-\(RN\).*jid=26a8ee92a424ed2d")
    check_visited_path(judge, traj, "second_company", r"/co/BAYADA-Home-Health-Care")
    check_visited_path(judge, traj, "reset", r"reset|location=New\+York,?\s*NY?(&|$)|/jobs-search\?search=registered\+nurse&location=New\+York")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 24)
    check_answer_number(judge, answer, "quick", 9)
    check_answer_number(judge, answer, "quick5", 5)
    check_answer_phrase(judge, answer, "first_title", "Registered Nurse - Gastroenterology")
    check_answer_phrase(judge, answer, "first_co", "Park Ave Gastroenterology")
    check_answer_phrase(judge, answer, "first_city", "Huntington, NY")
    check_answer_phrase(judge, answer, "first_pay", "$40 - $50/hr")
    check_answer_phrase(judge, answer, "posted", "23 hours ago")
    check_answer_phrase(judge, answer, "employment", "Part Time")
    check_answer_phrase(judge, answer, "second_co_industry", "Health Care and Social Assistance")
    check_answer_phrase(judge, answer, "second_co_size", "10000+ employees")
    check_answer_phrase(judge, answer, "second_co_hq", "Moorestown, NJ")
    check_answer_phrase(judge, answer, "f1", "CareOne")
    check_answer_phrase(judge, answer, "f1_pay", "$39 - $57/hr")
    check_answer_phrase(judge, answer, "f2", "BAYADA Home Health Care")
    check_answer_phrase(judge, answer, "f3", "Care One Enterprise")
    check_answer_phrase(judge, answer, "f4", "Care Options for Kids")
    check_answer_phrase(judge, answer, "f5", "Atlantic Rehabilitation Institute")
    check_answer_phrase(judge, answer, "highest", "$85K - $89K/yr")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
