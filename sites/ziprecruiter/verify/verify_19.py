#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--19 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r3 — carried from r2 where
unchanged, re-verified by the reviewer's two independent Playwright rounds
on the r3 re-review container wh-ziprecruiter-r3-review, seed md5
4f1cd6ceed444d093e80db2b0b35a0de) — never read from tasks.jsonl.
r3 sync (3ee7b98b): the re-anchored text routes through the first
title's OWN page (/Jobs/receptionist, "26 open Receptionist roles in this
snapshot") before its salary page, so the title-page visit is back as a
required gesture and its open-roles count is a new gated question point
(the r2 direct-salary-link shortcut no longer satisfies the text).

Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_chi", r"/jobs-search\?search=teacher.*location=Chicago")
    check_visited_path(judge, traj, "job_detail", r"/Job/Travel-Special-Education-Teacher")
    check_visited_path(judge, traj, "company", r"/co/")
    check_visited_path(judge, traj, "serp_la", r"/jobs-search\?search=receptionist.*location=Los\+Angeles")
    check_visited_path(judge, traj, "days5", r"days=5")
    check_visited_path(judge, traj, "browse", r"/browse$")
    check_visited_path(judge, traj, "letter_r", r"/browse/titles/R")
    check_visited_path(judge, traj, "title_page", r"/Jobs/receptionist")
    check_visited_path(judge, traj, "salary", r"/Salaries/receptionist-Salary")
    # -- answer ground truth --
    check_answer_number(judge, answer, "teacher_chi", 21)
    check_answer_phrase(judge, answer, "first_title", "Travel Special Education Teacher")
    check_answer_phrase(judge, answer, "first_posted", "2 days ago")
    check_answer_phrase(judge, answer, "first_employment", "Other")
    check_answer_phrase(judge, answer, "first_pay", "$2.3K - $2.5K/wk")
    check_answer_phrase(judge, answer, "co_industry", "Recruiting and Staffing Services")
    check_answer_number(judge, answer, "co_open", 1)
    check_answer_number(judge, answer, "rec_la", 19)
    check_answer_number(judge, answer, "rec_days5", 9)
    check_answer_phrase(judge, answer, "rec_first_title", "EXPERIENCED Dental Office Treatment Coordinator / Receptionist")
    check_answer_phrase(judge, answer, "rec_first_co", "Restore Dental")
    check_answer_phrase(judge, answer, "rec_first_pay", "$20 - $35/hr")
    check_answer_phrase(judge, answer, "r_title1", "Receptionist")
    check_answer_phrase(judge, answer, "r_title2", "Registered Nurse")
    check_answer_number(judge, answer, "r_count", 2)
    check_answer_regex(judge, answer, "title_open_roles", r"26 open Receptionist roles")
    check_answer_number(judge, answer, "salary_avg", "37,057")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
