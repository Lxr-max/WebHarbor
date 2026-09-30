#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--2 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the company question re-anchors from
the r1-defective industry/headquarters asks (Matter Family Office carries
neither in the capture) to the open-job count; adds the second $70K+
listing and the within-10-days first job's title; adds the highest pay
range among the unfiltered results.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_den", r"/jobs-search\?search=accountant.*location=Denver")
    check_visited_path(judge, traj, "smin_filter", r"smin=70000")
    check_visited_path(judge, traj, "job_detail", r"/Job/Senior-Accountant.*jid=3770eecfc82fcf30")
    check_visited_path(judge, traj, "company", r"/co/Matter-Family-Office")
    check_visited_path(judge, traj, "second_detail", r"/Job/Staff-Accountant.*jid=882b3e7b4d97f397")
    check_visited_path(judge, traj, "days10", r"days=10")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 12)
    check_answer_number(judge, answer, "smin70", 4)
    check_answer_phrase(judge, answer, "first_title", "Senior Accountant")
    check_answer_phrase(judge, answer, "first_co", "Matter Family Office")
    check_answer_phrase(judge, answer, "first_pay", "$80K - $100K/yr")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_phrase(judge, answer, "posted", "yesterday")
    check_answer_number(judge, answer, "open_jobs", 1)
    check_answer_phrase(judge, answer, "second_title", "Staff Accountant")
    check_answer_phrase(judge, answer, "second_co", "ELECTRO MAGNETIC APPLICATIONS INC")
    check_answer_phrase(judge, answer, "second_pay", "$70K - $90K/yr")
    check_answer_number(judge, answer, "days10", 10)
    check_answer_phrase(judge, answer, "days10_first_title", "Senior Accountant")
    check_answer_phrase(judge, answer, "days10_posted", "today")
    check_answer_phrase(judge, answer, "highest_pay", "$80K - $100K/yr")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
