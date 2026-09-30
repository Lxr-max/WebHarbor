#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--14 (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.

Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "blog", r"/blog/$")
    check_visited_path(judge, traj, "veterans", r"/blog/category/career-advice/veterans/")
    check_visited_path(judge, traj, "article1", r"/blog/job-search-tips-for-veterans/")
    check_visited_path(judge, traj, "article2", r"/blog/the-12-best-job-industries-for-veterans/")
    check_visited_path(judge, traj, "serp_ele", r"/jobs-search\?search=electrician.*location=Houston")
    check_visited_path(judge, traj, "days5", r"days=5")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    # -- answer ground truth --
    check_answer_number(judge, answer, "veterans_count", 2)
    check_answer_phrase(judge, answer, "a1_title", "Job Search Tips Every Military Veteran Should Know")
    check_answer_phrase(judge, answer, "a1_author", "Julia Pollak")
    check_answer_phrase(judge, answer, "a1_published", "2020-11-10")
    check_answer_phrase(judge, answer, "a1_updated", "2022-06-16")
    check_answer_count_at_least(judge, answer, "a1_tips", ["Where should I look for work", "What should I do if I don't have any work experience", "What kinds of industries should I explore", "How much should I expect to earn"], 4)
    check_answer_phrase(judge, answer, "a2_title", "The 12 Best Job Industries For Veterans")
    check_answer_phrase(judge, answer, "a2_author", "Kat Boogaard")
    check_answer_any(judge, answer, "a2_published", ["2017-10-20"])
    check_answer_phrase(judge, answer, "hot_title", "Dressing for Hot Weather Job Interviews")
    check_answer_phrase(judge, answer, "hot_cat", "The Hiring Process")
    check_answer_phrase(judge, answer, "hot_author", "Nicole Cavazos")
    check_answer_phrase(judge, answer, "hot_published", "2018-08-24")
    check_answer_number(judge, answer, "ele_hou", 17)
    check_answer_number(judge, answer, "ele_days5", 4)
    check_answer_number(judge, answer, "ele_quick", 4)
    check_answer_phrase(judge, answer, "first_co", "FALCON CONTROL SYSTEMS")
    check_answer_phrase(judge, answer, "first_pay", "$20 - $40/hr")
    check_answer_phrase(judge, answer, "first_posted", "19 hours ago")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
