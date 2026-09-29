#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--13 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the old Tips & Advice count question
(category permanently empty — the r1 data defect) becomes the Work Life
category article count plus its first article's title; the blog category
tree is now article-data-driven (the empty tips-advice category is gone).
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "blog", r"/blog/$")
    check_visited_path(judge, traj, "trends", r"/blog/category/career-advice/trends/")
    check_visited_path(judge, traj, "article", r"/blog/salary_exp/")
    check_visited_path(judge, traj, "work_life", r"/blog/category/career-advice/work-life/")
    check_visited_path(judge, traj, "work_life_first", r"/blog/rise-of-stay-at-home-dads/")
    check_visited_path(judge, traj, "serp_da", r"/jobs-search\?search=data\+analyst.*location=Seattle")
    check_visited_path(judge, traj, "days5", r"days=5")
    # -- answer ground truth --
    check_answer_number(judge, answer, "blog_cats", 7)
    check_answer_number(judge, answer, "trends_count", 5)
    check_answer_phrase(judge, answer, "article_title", "4 Top Industry Insights to Fuel Your Job Search")
    check_answer_phrase(judge, answer, "author", "The ZipRecruiter Editors")
    check_answer_phrase(judge, answer, "published", "2023-03-07")
    check_answer_count_at_least(judge, answer, "insights", ["There Are More Jobs", "Jobs Offer More Flexibility", "Workplaces Want to Be More Diverse", "Perks and Benefits Are a Priority"], 4)
    check_answer_any(judge, answer, "hottest", ["There Are More Jobs", "more jobs"])
    check_answer_any(judge, answer, "other_trends", ["Job News Roundup", "Who's Hiring Now", "COVID-19 Resources for Job Seekers"])
    check_answer_number(judge, answer, "worklife_count", 2)
    check_answer_phrase(judge, answer, "worklife_first", "The Rise of Stay-at-Home Dads")
    check_answer_number(judge, answer, "da_sea", 20)
    check_answer_number(judge, answer, "da_days5", 4)
    check_answer_phrase(judge, answer, "first_co", "DKMRBH Inc")
    check_answer_phrase(judge, answer, "first_pay", "$50 - $55/hr")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
