#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--7 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the San Francisco jobs page is now
reached through the company profile's Jobs-by-location link (inlinked,
no URL construction); size renders upstream-lowercase "employees"; the
within-5-days first result gains its quick-apply status and the second
result gains company and city.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_swe_sf", r"/jobs-search\?search=software\+engineer.*location=San\+Francisco")
    check_visited_path(judge, traj, "job_detail", r"/Job/Forward-Deployed-Software-Engineer.*jid=5f4b2c55241a752f")
    check_visited_path(judge, traj, "company", r"/co/Veritus$")
    check_visited_path(judge, traj, "sf_jobs", r"/co/Veritus/Jobs/-in-San-Francisco,CA")
    check_visited_path(judge, traj, "days5", r"days=5")
    check_visited_path(judge, traj, "second", r"/Job/Forward-Deployed-Software-Engineer.*jid=9a713d7fb28b2011")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "title", "Forward Deployed Software Engineer")
    check_answer_phrase(judge, answer, "co", "Veritus")
    check_answer_phrase(judge, answer, "loc", "San Francisco, CA")
    check_answer_phrase(judge, answer, "loc_type", "On-site")
    check_answer_phrase(judge, answer, "employment", "Full Time")
    check_answer_phrase(judge, answer, "posted", "7 hours ago")
    check_answer_phrase(judge, answer, "badge", "New")
    check_answer_regex(judge, answer, "badge_quick_negated", r"not a quick apply|no quick apply|isn.t a quick apply")
    check_answer_phrase(judge, answer, "industry", "Offices of Mental Health Practitioners")
    check_answer_phrase(judge, answer, "size", "11 - 50 employees")
    check_answer_phrase(judge, answer, "platform", "OpenAI")
    check_answer_phrase(judge, answer, "hq", "New York, NY")
    check_answer_phrase(judge, answer, "website", "veritussolutions.com")
    check_answer_number(judge, answer, "open_jobs", 11)
    check_answer_number(judge, answer, "sf_jobs", 1)
    check_answer_number(judge, answer, "days5", 13)
    check_answer_phrase(judge, answer, "days5_posted", "7 hours ago")
    check_answer_regex(judge, answer, "days5_quick_negated", r"not a quick apply|no quick apply|isn.t a quick apply")
    check_answer_phrase(judge, answer, "days5_second_co", "Veritus")
    check_answer_phrase(judge, answer, "days5_second_city", "Alameda, CA")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
