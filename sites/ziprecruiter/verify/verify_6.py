#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--6 (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.

Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_dal", r"/jobs-search\?search=warehouse.*location=Dallas")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "job_detail", r"/Job/Forklift-Operator.*jid=024f93e335f888a9")
    check_visited_path(judge, traj, "company", r"/co/Proman-Staffing")
    check_visited_path(judge, traj, "second", r"/Job/Cold-Environment-Warehouse-Packers")
    check_visited_path(judge, traj, "days5", r"days=5")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 17)
    check_answer_number(judge, answer, "quick", 8)
    check_answer_phrase(judge, answer, "first_title", "Forklift Operator")
    check_answer_phrase(judge, answer, "first_co", "Proman Staffing")
    check_answer_phrase(judge, answer, "first_city", "Fort Worth, TX")
    check_answer_phrase(judge, answer, "first_pay", "$16.25 - $19.25/hr")
    check_answer_phrase(judge, answer, "posted", "8 hours ago")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_number(judge, answer, "company_open", 1)
    check_answer_phrase(judge, answer, "second_title", "Cold Environment Warehouse Packers")
    check_answer_phrase(judge, answer, "second_pay", "$13.50 - $14.50/hr")
    check_answer_phrase(judge, answer, "second_city", "Grand Prairie, TX")
    check_answer_number(judge, answer, "days5", 10)

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
