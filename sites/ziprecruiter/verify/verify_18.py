#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--18 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): adds the job page question points
(pay, location type, posted age) reached from My Applications, and the
weekly staff-accountant alert creation with the full alerts table.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "login", r"/authn/login")
    check_visited_path(judge, traj, "profile", r"/jobseeker/profile")
    check_visited_path(judge, traj, "resume", r"/jobseeker/resume")
    check_visited_path(judge, traj, "applications", r"/jobseeker/applications")
    check_visited_path(judge, traj, "job_detail", r"/Job/Senior-Accountant.*jid=3770eecfc82fcf30")
    check_visited_path(judge, traj, "alerts", r"/jobseeker/alerts")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "resume_title", "Senior Accountant (CPA)")
    check_answer_phrase(judge, answer, "resume_summary", "CPA with 8 years across public accounting and industry; month-end close, audit readiness, NetSuite.")
    check_answer_phrase(judge, answer, "exp1_role", "Senior Accountant")
    check_answer_phrase(judge, answer, "exp1_co", "Matter Family Office")
    check_answer_phrase(judge, answer, "exp1_dates", "2022-04")
    check_answer_phrase(judge, answer, "exp2_role", "Staff Accountant II")
    check_answer_phrase(judge, answer, "exp2_co", "Caribou Financial")
    check_answer_phrase(judge, answer, "exp2_dates", "2019-06")
    check_answer_phrase(judge, answer, "edu1", "BS, Accounting")
    check_answer_phrase(judge, answer, "edu1_school", "Metro State Denver")
    check_answer_phrase(judge, answer, "edu2", "CPA license")
    check_answer_count_at_least(judge, answer, "skills", ["NetSuite", "Month-end close", "GAAP", "Excel", "Audit prep", "SQL"], 6)
    check_answer_phrase(judge, answer, "new_skill", "QuickBooks")
    check_answer_number(judge, answer, "skill_count", 7)
    check_answer_phrase(judge, answer, "updated_at", "2026-09-29")
    check_answer_phrase(judge, answer, "app_title", "Senior Accountant")
    check_answer_phrase(judge, answer, "app_co", "Matter Family Office")
    check_answer_phrase(judge, answer, "app_city", "Denver, CO")
    check_answer_phrase(judge, answer, "app_status", "Withdrawn")
    check_answer_phrase(judge, answer, "app_tl1", "2026-09-20")
    check_answer_phrase(judge, answer, "app_tl2", "2026-09-22")
    check_answer_phrase(judge, answer, "app_tl3", "2026-09-25")
    check_answer_phrase(judge, answer, "job_pay", "$80K - $100K/yr")
    check_answer_phrase(judge, answer, "job_loc_type", "On-site")
    check_answer_phrase(judge, answer, "job_posted", "yesterday")
    check_answer_phrase(judge, answer, "alert1", "accountant")
    check_answer_phrase(judge, answer, "alert1_loc", "Denver, CO")
    check_answer_phrase(judge, answer, "alert1_freq", "Daily")
    check_answer_phrase(judge, answer, "alert2", "remote bookkeeping")
    check_answer_phrase(judge, answer, "alert2_loc", "Anywhere")
    check_answer_phrase(judge, answer, "alert2_freq", "Weekly")
    check_answer_phrase(judge, answer, "alert3", "staff accountant")
    check_answer_phrase(judge, answer, "alert3_loc", "Denver, CO")
    check_answer_phrase(judge, answer, "alert3_freq", "Weekly")
    # -- DB after-state: resume edit + exactly one new weekly alert --
    check_only_tables_changed(judge, initial, after, {"resumes", "job_alerts"})
    check_row_matches(judge, after, "SELECT COUNT(*) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com' AND r.skills LIKE '%QuickBooks%'", (), "quickbooks_added")
    check_row_matches(judge, after, "SELECT json_array_length(r.skills) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com'", (), "skills_len")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM resumes r JOIN users u ON u.id=r.user_id WHERE u.email='dana.k@test.com' AND r.updated_at='2026-09-29'", (), "updated_at_moved")
    check_row_matches(judge, after, "SELECT 1 FROM job_alerts WHERE term='staff accountant' AND location='Denver, CO' AND frequency='weekly' AND user_id=(SELECT id FROM users WHERE email='dana.k@test.com')", (), "new_alert_row")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
