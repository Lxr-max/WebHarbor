#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--8 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task re-anchored at 4d57185b): the first listing's company
(CareOne) jobs-page question moves from the New York page (upstream
unmapped in this snapshot) to the East Brunswick page — its real capture
location, now reachable through the company profile's Jobs-by-location
link.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_rn_ny", r"/jobs-search\?search=registered\+nurse.*location=New\+York")
    check_visited_path(judge, traj, "job_detail", r"/Job/Registered-Nurse.*jid=32e068cf8f4557af")
    check_visited_path(judge, traj, "company", r"/co/CareOne$")
    check_visited_path(judge, traj, "eb_jobs", r"/co/CareOne/Jobs/-in-East-Brunswick,NJ")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "second", r"/Job/Private-Duty-Registered-Nurse")
    check_visited_path(judge, traj, "breakroom_co", r"/co/BAYADA-Home-Health-Care")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "title", "Registered Nurse")
    check_answer_phrase(judge, answer, "co", "CareOne")
    check_answer_phrase(judge, answer, "city", "East Brunswick, NJ")
    check_answer_phrase(judge, answer, "pay", "$39 - $57/hr")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_phrase(judge, answer, "posted", "21 days ago")
    check_answer_number(judge, answer, "company_open", 1)
    check_answer_number(judge, answer, "eb_jobs", 1)
    check_answer_number(judge, answer, "quick", 9)
    check_answer_phrase(judge, answer, "quick_first_co", "Park Ave Gastroenterology")
    check_answer_phrase(judge, answer, "quick_first_pay", "$40 - $50/hr")
    check_answer_phrase(judge, answer, "second_title", "Private Duty Registered Nurse (RN)")
    check_answer_phrase(judge, answer, "second_city", "Hoboken, NJ")
    check_answer_phrase(judge, answer, "second_pay", "$35 - $45/hr")
    check_answer_number(judge, answer, "breakroom_score", "6.87")
    check_answer_number(judge, answer, "breakroom_count", 257)

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
