#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--0 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r3 from the reviewer's two
independent Playwright rounds on the r3 re-review container
wh-ziprecruiter-r3-review, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r3 sync (task re-anchored at 3ee7b98b): the "San Francisco roles
count" question point becomes the company's San Francisco JOBS-PAGE roles
count (T7-style, /co/YO-AI-Labs/Jobs/-in-San-Francisco,CA "1 open roles
from YO AI Labs in this snapshot"), so opening that page is now a required
gesture and is gated; the second within-5-days result's company and city
and the lowercase "employees" size rendering carry over from r2.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco")
    check_visited_path(judge, traj, "remote_filter", r"remote=remote")
    check_visited_path(judge, traj, "job_detail", r"/Job/Software-Engineer-Open-Source-Contributions-Remote.*jid=032e0b0150231b0d")
    check_visited_path(judge, traj, "company", r"/co/YO-AI-Labs")
    check_visited_path(judge, traj, "sf_jobs_page", r"/co/YO-AI-Labs/Jobs/-in-San-Francisco,CA")
    check_visited_path(judge, traj, "days5", r"days=5")
    check_visited_path(judge, traj, "second_result", r"/Job/Forward-Deployed-Software-Engineer.*jid=9a713d7fb28b2011")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base_count", 22)
    check_answer_number(judge, answer, "remote_count", 1)
    check_answer_phrase(judge, answer, "remote_first_title", "Software Engineer - Open Source Contributions - Remote")
    check_answer_phrase(judge, answer, "remote_first_co", "YO AI Labs")
    check_answer_phrase(judge, answer, "remote_first_pay", "$50 - $100/hr")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_phrase(judge, answer, "posted", "3 days ago")
    check_answer_phrase(judge, answer, "industry", "Computing Infrastructure Providers, Data Processing, Web Hosting")
    check_answer_phrase(judge, answer, "size", "201 - 500 employees")
    check_answer_phrase(judge, answer, "hq", "Abu Dhabi, Abu Dhabi, AE")
    check_answer_regex(judge, answer, "sf_jobs_page", r"1 open roles from YO AI Labs")
    check_answer_number(judge, answer, "days5_count", 13)
    check_answer_phrase(judge, answer, "days5_first", "Forward Deployed Software Engineer")
    check_answer_phrase(judge, answer, "days5_posted", "7 hours ago")
    check_answer_regex(judge, answer, "days5_quick_negated", r"not a quick apply|no quick apply|isn.t a quick apply")
    check_answer_phrase(judge, answer, "days5_second_co", "Veritus")
    check_answer_phrase(judge, answer, "days5_second_city", "Alameda, CA")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
