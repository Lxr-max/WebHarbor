#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--4 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): the senior first listing gains
location/posted-age/quick-apply question points and its company's
open-job count; the junior first listing gains its posted age, location
type and company; the no-experience count gains the first listing's
company.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_swe", r"/jobs-search\?search=software\+engineer(&|$|&)")
    check_visited_path(judge, traj, "senior", r"exp=senior")
    check_visited_path(judge, traj, "job_detail", r"/Job/Senior-Software-Engineer.*jid=")
    check_visited_path(judge, traj, "company", r"/co/Burnt")
    check_visited_path(judge, traj, "junior", r"exp=junior")
    check_visited_path(judge, traj, "junior_detail", r"/Job/Software-Engineer-I-&-II.*jid=dd925abcdc7a06f8")
    check_visited_path(judge, traj, "none", r"exp=none")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 76)
    check_answer_number(judge, answer, "senior", 12)
    check_answer_phrase(judge, answer, "senior_first", "Senior Software Engineer")
    check_answer_phrase(judge, answer, "senior_co", "Burnt")
    check_answer_phrase(judge, answer, "senior_pay", "$144K - $190K/yr")
    check_answer_phrase(judge, answer, "loc", "San Francisco, CA")
    check_answer_phrase(judge, answer, "posted", "2 days ago")
    check_answer_regex(judge, answer, "quick_negated", r"not a quick apply|no quick apply|isn.t a quick apply")
    check_answer_number(judge, answer, "company_open", 1)
    check_answer_number(judge, answer, "junior", 1)
    check_answer_phrase(judge, answer, "junior_first", "Software Engineer I & II")
    check_answer_phrase(judge, answer, "junior_co", "Tek Fusion Global")
    check_answer_phrase(judge, answer, "junior_pay", "$55K - $95K/yr")
    check_answer_phrase(judge, answer, "junior_posted", "11 days ago")
    check_answer_phrase(judge, answer, "junior_loc_type", "On-site")
    check_answer_number(judge, answer, "none", 2)
    check_answer_phrase(judge, answer, "none_first_co", "RFA Engineering")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
