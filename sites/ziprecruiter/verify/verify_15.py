#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--15 (ziprecruiter).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
Playwright rounds on the review container wh-ziprecruiter-review, seed md5
6d6830746bd74d5b19b91c983dec0c3c) — never read from tasks.jsonl.
Stateful: exactly one non-benchmark user (+profile), one application and
one application event for the first quick-apply Dallas warehouse job
(Forklift Operator, jid 024f93e335f888a9). The verifier pins the delta
shape, not the agent-chosen email.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "register", r"/authn/register")
    check_visited_path(judge, traj, "serp", r"/jobs-search\?search=warehouse.*location=Dallas")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "job_detail", r"/Job/Forklift-Operator.*jid=024f93e335f888a9")
    check_visited_path(judge, traj, "apply_done", r"/apply/done/024f93e335f888a9")
    check_visited_path(judge, traj, "applications", r"/jobseeker/applications")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "confirm_heading", "Application sent")
    check_answer_phrase(judge, answer, "job_title", "Forklift Operator")
    check_answer_phrase(judge, answer, "job_co", "Proman Staffing")
    check_answer_phrase(judge, answer, "status", "Applied")
    check_answer_phrase(judge, answer, "timeline_note", "1-Click Application submitted")
    check_answer_number(judge, answer, "base", 17)
    check_answer_number(judge, answer, "quick", 8)
    check_answer_number(judge, answer, "saved_start", 0)

    check_only_tables_changed(judge, initial, after, {"users", "profiles", "applications", "application_events"})
    check_rows_added(judge, initial, after, "users", 1)
    check_rows_added(judge, initial, after, "profiles", 1)
    check_rows_added(judge, initial, after, "applications", 1)
    check_rows_added(judge, initial, after, "application_events", 1)
    check_row_matches(judge, after, "SELECT COUNT(*) FROM users WHERE is_benchmark=0", (), "new_user_nonbenchmark")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM applications a JOIN jobs j ON j.id=a.job_id WHERE j.jid='024f93e335f888a9'", (), "app_for_proman_forklift")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM application_events WHERE note='1-Click Application submitted' AND occurred_at='2026-09-29'", (), "app_event_row")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
