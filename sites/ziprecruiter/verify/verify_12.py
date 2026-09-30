#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--12 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (4d57185b): task text unchanged, ground-truth numbers unchanged;
the navigation gates move to the mirror's new linked routes — the
Accountant salary page opens through Browse's "Browse salaries instead"
index (/browse/salaries) and the Denver city salary page through the
footer's Search Salaries index (the r1 goto-only construction is gone).
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "browse", r"/browse$")
    check_visited_path(judge, traj, "browse_salaries", r"/browse/salaries")
    check_visited_path(judge, traj, "salary_national", r"/Salaries/accountant-Salary$")
    check_visited_path(judge, traj, "serp_den", r"/jobs-search\?search=accountant.*location=Denver")
    check_visited_path(judge, traj, "smin", r"smin=70000")
    check_visited_path(judge, traj, "job_detail", r"/Job/Senior-Accountant.*jid=3770eecfc82fcf30")
    check_visited_path(judge, traj, "days10", r"days=10")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "salary_denver", r"/Salaries/accountant-Salary-in-Denver,CO")
    # -- answer ground truth --
    check_answer_number(judge, answer, "avg_year", "68,326")
    check_answer_number(judge, answer, "avg_hour", "32.85")
    check_answer_number(judge, answer, "median", "68,326")
    check_answer_number(judge, answer, "p75", "78,500")
    check_answer_number(judge, answer, "bands_ge15", 4)
    check_answer_number(judge, answer, "den_jobs", 12)
    check_answer_number(judge, answer, "den_70", 4)
    check_answer_phrase(judge, answer, "first_title", "Senior Accountant")
    check_answer_phrase(judge, answer, "first_co", "Matter Family Office")
    check_answer_phrase(judge, answer, "first_pay", "$80K - $100K/yr")
    check_answer_phrase(judge, answer, "posted", "yesterday")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_number(judge, answer, "days10", 10)
    check_answer_number(judge, answer, "quick", 2)
    check_answer_number(judge, answer, "denver_avg", "70,327")
    check_answer_number(judge, answer, "denver_p25", "55,100")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
