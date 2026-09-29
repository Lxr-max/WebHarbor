#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--9 (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.

Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco")
    check_visited_path(judge, traj, "job_detail", r"/Job/Forward-Deployed-Software-Engineer")
    check_visited_path(judge, traj, "company", r"/co/Veritus")
    check_visited_path(judge, traj, "remote", r"remote=remote")
    check_visited_path(judge, traj, "days5", r"days=5")
    check_visited_path(judge, traj, "browse", r"/browse$")
    check_visited_path(judge, traj, "letter_s", r"/browse/titles/S")
    check_visited_path(judge, traj, "title_page", r"/Jobs/software-engineer$")
    check_visited_path(judge, traj, "salary", r"/Salaries/software-engineer-Salary")
    check_visited_path(judge, traj, "nearby", r"/Job/Full-Stack-Software-Engineer--PRO-Team")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 22)
    check_answer_phrase(judge, answer, "loc_type", "On-site")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_phrase(judge, answer, "posted", "7 hours ago")
    check_answer_phrase(judge, answer, "industry", "Offices of Mental Health Practitioners")
    check_answer_phrase(judge, answer, "hq", "New York, NY")
    check_answer_number(judge, answer, "remote", 1)
    check_answer_number(judge, answer, "days5", 1)
    check_answer_number(judge, answer, "roles", 76)
    check_answer_number(judge, answer, "avg", "147,524")
    check_answer_number(judge, answer, "avg_hour", "70.92")
    check_answer_number(judge, answer, "p25", "120,000")
    check_answer_phrase(judge, answer, "nearby_title", "Full-Stack Software Engineer -- PRO Team")
    check_answer_phrase(judge, answer, "nearby_co", "Viome Life Sciences")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
