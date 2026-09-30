#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--11 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r3 from the reviewer's two
independent Playwright rounds on the r3 re-review container
wh-ziprecruiter-r3-review, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r3 sync (3ee7b98b): the re-anchored text asks, after the first nearby
job's title and company, for ITS COMPANY PROFILE's open-roles count
(/co/Eitacies-Inc "1 open roles from Eitacies Inc in this snapshot"), so
the profile visit is now a required gesture and is gated, and the
nationwide search runs from the company page's header search (the r2
non-required browser-back is gone from the honest path).
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "browse", r"/browse$")
    check_visited_path(judge, traj, "letter_s", r"/browse/titles/S")
    check_visited_path(judge, traj, "swe_title", r"/Jobs/software-engineer$")
    check_visited_path(judge, traj, "salary_national", r"/Salaries/Software-Engineer-Salary$|/Salaries/software-engineer-Salary$")
    check_visited_path(judge, traj, "salary_sf", r"/Salaries/Software-Engineer-Salary-in-San-Francisco,CA|/Salaries/software-engineer-Salary-in-San-Francisco,CA")
    check_visited_path(judge, traj, "nearby", r"/Job/Software-Developer-and-SRE.*jid=56174553f29035b0")
    check_visited_path(judge, traj, "nearby_co_profile", r"/co/Eitacies-Inc")
    check_visited_path(judge, traj, "serp", r"/jobs-search\?search=software\+engineer(&|$)")
    check_visited_path(judge, traj, "senior", r"exp=senior")
    check_visited_path(judge, traj, "remote", r"remote=remote")
    check_visited_path(judge, traj, "job_detail", r"/Job/Senior-Staff-Software-Engineer")
    # -- answer ground truth --
    check_answer_number(judge, answer, "avg_year", "147,524")
    check_answer_number(judge, answer, "avg_hour", "70.92")
    check_answer_number(judge, answer, "median", "147,524")
    check_answer_number(judge, answer, "p10", "95,500")
    check_answer_number(judge, answer, "p90", "205,000")
    check_answer_number(judge, answer, "sf_avg_year", "173,808")
    check_answer_number(judge, answer, "sf_avg_hour", "83.56")
    check_answer_number(judge, answer, "sf_median", "173,808")
    check_answer_number(judge, answer, "sf_p25", "141,400")
    check_answer_phrase(judge, answer, "nearby_title", "Software Developer and SRE")
    check_answer_phrase(judge, answer, "nearby_co", "Eitacies Inc")
    check_answer_regex(judge, answer, "nearby_open_roles", r"1 open roles from Eitacies Inc")
    check_answer_number(judge, answer, "national_jobs", 76)
    check_answer_number(judge, answer, "senior", 12)
    # the senior+remote count is 1 and the re-frozen answer carries another
    # legitimate 1 (the Eitacies open-roles count), so the count is bound to
    # its question context (a digit 1 adjacent to "remote"), not to any 1
    # token in the answer
    check_answer_regex(judge, answer, "senior_remote", r"[Rr]emote[^.\n]{0,30}?\b1\b|\b1\b[^.\n]{0,30}?[Rr]emote")
    check_answer_phrase(judge, answer, "first_title", "Senior/Staff Software Engineer, Platform")
    check_answer_phrase(judge, answer, "first_co", "AIDA Recruitment")
    check_answer_phrase(judge, answer, "first_pay", "$150K - $350K/yr")
    check_answer_phrase(judge, answer, "first_posted", "6 days ago")
    check_answer_phrase(judge, answer, "city1", "Soledad, CA")
    check_answer_number(judge, answer, "city1_avg", "220,681")
    check_answer_phrase(judge, answer, "city2", "Portola Valley, CA")
    check_answer_number(judge, answer, "city2_avg", "205,618")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
