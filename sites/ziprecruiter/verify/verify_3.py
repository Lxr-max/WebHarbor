#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--3 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the Part Time first listing now gets
real detail question points (posted age, employment type, pay-if-shown);
the Per Diem combination is now produced by the REAL checkbox panel
(request.args.getlist('et') fix — the r1 UI defect is gone, the combined
URL pattern gate remains accepted); the quick-apply first listing gains
its posted age.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_nurse", r"/jobs-search\?search=nurse")
    check_visited_path(judge, traj, "pt_filter", r"et=part_time")
    check_visited_path(judge, traj, "pt_first_detail", r"/Job/Part-Time-Licensed-Practical-Nurse-\(LPN\)-West-Hartford.*jid=861167288e55165b")
    check_visited_path(judge, traj, "combined", r"et=part_time,per_diem|et=per_diem&.*et=part_time|et=part_time&.*et=per_diem")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "quick_first_detail", r"/Job/LPN-Corrections-Nurse.*jid=0fc738d4ef03ba71")
    check_visited_path(judge, traj, "exp_none", r"exp=none")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 124)
    check_answer_number(judge, answer, "pt", 27)
    check_answer_phrase(judge, answer, "pt_first_title", "Part-Time Licensed Practical Nurse (LPN) - West Hartford")
    check_answer_phrase(judge, answer, "pt_first_co", "GameDay Men's Health - West Hartford")
    check_answer_phrase(judge, answer, "pt_first_city", "West Hartford, CT")
    check_answer_any(judge, answer, "pt_first_pay", ["no pay", "not shown", "no salary", "none shown", "pay is not"])
    check_answer_phrase(judge, answer, "pt_first_posted", "today")
    check_answer_phrase(judge, answer, "pt_first_employment", "Part Time")
    check_answer_number(judge, answer, "pt_pd", 29)
    check_answer_phrase(judge, answer, "ptpd_first_title", "Part-Time Licensed Practical Nurse (LPN) - West Hartford")
    check_answer_number(judge, answer, "quick", 78)
    check_answer_phrase(judge, answer, "quick_first_co", "Supplemental Health Care")
    check_answer_phrase(judge, answer, "quick_first_loc", "Oregon, WI")
    check_answer_phrase(judge, answer, "quick_first_pay", "$1.3K - $1.4K/wk")
    check_answer_phrase(judge, answer, "quick_first_posted", "11 hours ago")
    check_answer_number(judge, answer, "quick_none", 0)

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
