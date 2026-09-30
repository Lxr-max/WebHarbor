#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--17 (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.
Stateful: one saved job removed (the most recent save — the YO AI Labs
Open Source listing), one weekly data-engineer alert created.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "login", r"/authn/login")
    check_visited_path(judge, traj, "profile", r"/jobseeker/profile")
    check_visited_path(judge, traj, "applications", r"/jobseeker/applications")
    check_visited_path(judge, traj, "job_detail", r"/Job/Software-Engineer.*jid=19d6f9232eedc0f5|/c/JOLT/")
    check_visited_path(judge, traj, "resume", r"/jobseeker/resume")
    check_visited_path(judge, traj, "saved", r"/jobseeker/saved-jobs")
    check_visited_path(judge, traj, "alerts", r"/jobseeker/alerts")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "app_title", "Software Engineer")
    check_answer_phrase(judge, answer, "app_co", "JOLT")
    check_answer_phrase(judge, answer, "app_city", "San Francisco, CA")
    check_answer_phrase(judge, answer, "applied_at", "2026-09-21")
    check_answer_phrase(judge, answer, "status", "Interviewing")
    check_answer_phrase(judge, answer, "tl1", "2026-09-21")
    check_answer_phrase(judge, answer, "tl1_note", "1-Click Application submitted")
    check_answer_phrase(judge, answer, "tl2", "2026-09-23")
    check_answer_phrase(judge, answer, "tl2_note", "The employer viewed your application")
    check_answer_phrase(judge, answer, "tl3", "2026-09-27")
    check_answer_phrase(judge, answer, "tl3_note", "The employer invited you to schedule a phone screen")
    check_answer_phrase(judge, answer, "job_pay", "$125K - $135K/yr")
    check_answer_phrase(judge, answer, "job_loc_type", "On-site")
    check_answer_phrase(judge, answer, "job_posted", "17 days ago")
    check_answer_phrase(judge, answer, "resume_title", "Software Engineer — Full Stack")
    check_answer_phrase(judge, answer, "resume_updated", "2026-09-19")
    check_answer_phrase(judge, answer, "resume_complete", "complete")
    check_answer_phrase(judge, answer, "resume_summary", "Backend-leaning full-stack engineer; Python, Go, Postgres.")
    check_answer_phrase(judge, answer, "resume_exp", "JOLT")
    check_answer_count_at_least(judge, answer, "resume_skills", ["Python", "Go", "PostgreSQL", "React"], 4)
    check_answer_phrase(judge, answer, "remaining", "JOLT")
    check_answer_phrase(judge, answer, "alert_term", "data engineer")
    check_answer_phrase(judge, answer, "alert_loc", "Seattle, WA")
    check_answer_phrase(judge, answer, "alert_freq", "Weekly")

    check_only_tables_changed(judge, initial, after, {"saved_jobs", "job_alerts"})
    check_rows_removed(judge, initial, after, "saved_jobs", 1)
    check_rows_added(judge, initial, after, "job_alerts", 1)
    check_row_matches(judge, after, "SELECT COUNT(*) FROM job_alerts WHERE term='data engineer' AND location='Seattle, WA' AND frequency='weekly' AND user_id=(SELECT id FROM users WHERE email='bob.c@test.com')", (), "bob_new_alert")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM saved_jobs WHERE user_id=(SELECT id FROM users WHERE email='bob.c@test.com')", (), "bob_saved_after")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
