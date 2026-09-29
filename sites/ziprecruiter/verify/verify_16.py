#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--16 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the gastroenterology premise defect
is fixed — the task now names the Manhattan urology-employer listing
(New York Health), which is what Alice actually saved; the alert becomes
WEEKLY; adds the resume page question points, the Brooklyn listing's
posted age and employment type, and the full alerts table.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "login", r"/authn/login")
    check_visited_path(judge, traj, "profile", r"/jobseeker/profile")
    check_visited_path(judge, traj, "resume", r"/jobseeker/resume")
    check_visited_path(judge, traj, "saved", r"/jobseeker/saved-jobs")
    check_visited_path(judge, traj, "brooklyn_detail", r"/Job/Registered-Nurse-IV-Drip-Park-Slope.*jid=1b13c75885354910")
    check_visited_path(judge, traj, "alerts", r"/jobseeker/alerts")
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "headline", "Registered Nurse, BSN — 6 years ICU")
    check_answer_number(judge, answer, "years", 6)
    check_answer_phrase(judge, answer, "location", "Brooklyn, NY")
    check_answer_phrase(judge, answer, "resume_title", "Registered Nurse — ICU")
    check_answer_number(judge, answer, "resume_skills", 6)
    check_answer_phrase(judge, answer, "s1_title", "Registered Nurse (RN) - Bilingual Spanish/English (Urology)")
    check_answer_phrase(judge, answer, "s1_co", "New York Health")
    check_answer_phrase(judge, answer, "s1_city", "Manhattan, NY")
    check_answer_phrase(judge, answer, "s1_pay", "$52/hr")
    check_answer_phrase(judge, answer, "s2_title", "Registered Nurse IV Drip - Park Slope")
    check_answer_phrase(judge, answer, "s2_city", "Brooklyn, NY")
    check_answer_phrase(judge, answer, "s2_pay", "$52 - $54/hr")
    check_answer_phrase(judge, answer, "s3_title", "Registered Nurse (RN)")
    check_answer_phrase(judge, answer, "s3_co", "New York Cancer & Blood Specialists")
    check_answer_phrase(judge, answer, "s3_pay", "$52/hr")
    check_answer_phrase(judge, answer, "remaining2", "Brooklyn")
    check_answer_phrase(judge, answer, "remaining2b", "Manhattan")
    check_answer_phrase(judge, answer, "brooklyn_posted", "4 days ago")
    check_answer_phrase(judge, answer, "brooklyn_employment", "Part Time")
    check_answer_phrase(judge, answer, "alert_term", "licensed practical nurse")
    check_answer_phrase(judge, answer, "alert_loc", "Brooklyn, NY")
    check_answer_phrase(judge, answer, "alert_freq", "Weekly")
    check_answer_phrase(judge, answer, "alert1_term", "registered nurse")
    check_answer_phrase(judge, answer, "alert1_loc", "New York, NY")
    check_answer_phrase(judge, answer, "alert1_freq", "Daily")
    # -- DB after-state: unsave + exactly one new weekly alert --
    check_only_tables_changed(judge, initial, after, {"saved_jobs", "job_alerts"})
    check_rows_removed(judge, initial, after, "saved_jobs", 1)
    check_rows_added(judge, initial, after, "job_alerts", 1)
    check_row_matches(judge, after, "SELECT COUNT(*) FROM saved_jobs WHERE user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "alice_saved_count")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM saved_jobs s JOIN jobs j ON j.id=s.job_id JOIN companies c ON c.id=j.company_id WHERE c.slug='New-York-Health' AND s.user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "urology_unsaved")
    check_row_matches(judge, after, "SELECT COUNT(*) FROM job_alerts WHERE term='licensed practical nurse' AND location='Brooklyn, NY' AND frequency='weekly' AND user_id=(SELECT id FROM users WHERE email='alice.j@test.com')", (), "new_alert_row")
    check_row_matches(judge, after, "SELECT 1 FROM job_alerts a WHERE a.user_id=(SELECT id FROM users WHERE email='alice.j@test.com') AND (SELECT COUNT(*) FROM job_alerts WHERE user_id=(SELECT id FROM users WHERE email='alice.j@test.com'))=2", (), "alice_alerts_total_2")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
