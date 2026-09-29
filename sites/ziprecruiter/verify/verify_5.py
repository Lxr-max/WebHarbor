#!/usr/bin/env python3
"""Deterministic verifier for ZipRecruiter--5 (ziprecruiter).

Ground truth below is HARDCODED (re-frozen at r2 from the reviewer's two
independent Playwright rounds on the re-review container
wh-ziprecruiter-rereview, seed md5 4f1cd6ceed444d093e80db2b0b35a0de) —
never read from tasks.jsonl.
r2 sync (task deepened at 4d57185b): adds the most-recent listing's
company profile open-job count, the quick-apply first listing's
employment type and the full distinct-city roster of the unfiltered
results (the honest agent pages through every result page).
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "ZipRecruiter--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "serp_atl", r"/jobs-search\?search=truck\+driver.*location=Atlanta")
    check_visited_path(judge, traj, "page2", r"page=2")
    check_visited_path(judge, traj, "job_detail", r"/Job/CDL-A-Truck-Driver.*jid=")
    check_visited_path(judge, traj, "company", r"/co/Dollar-General-Fleet")
    check_visited_path(judge, traj, "quick", r"apply=quick")
    check_visited_path(judge, traj, "quick_first_detail", r"/Job/Local-Non-CDL-Box-Truck-Delivery-Driver-\(Atlanta\)")
    # -- answer ground truth --
    check_answer_number(judge, answer, "base", 21)
    check_answer_number(judge, answer, "pages", 2)
    check_answer_phrase(judge, answer, "p1_first", "CDL A Truck Driver")
    check_answer_phrase(judge, answer, "p1_co", "Dollar General Fleet")
    check_answer_phrase(judge, answer, "p1_pay", "$100K/yr")
    check_answer_phrase(judge, answer, "p2_first", "CDL A Truck Driver - Regional")
    check_answer_phrase(judge, answer, "p2_co", "Epes Transport Systems, Inc.")
    check_answer_phrase(judge, answer, "p2_pay", "$66K - $96K/yr")
    check_answer_phrase(judge, answer, "mr_posted", "18 days ago")
    check_answer_phrase(judge, answer, "mr_pay", "$100K/yr")
    check_answer_phrase(judge, answer, "mr_employment", "Full Time")
    check_answer_number(judge, answer, "company_open", 1)
    check_answer_number(judge, answer, "quick", 10)
    check_answer_phrase(judge, answer, "quick_pay", "$26 - $28/hr")
    check_answer_phrase(judge, answer, "quick_employment", "Full Time")
    check_answer_number(judge, answer, "n_cities", 7)
    check_answer_phrase(judge, answer, "city1", "Acworth")
    check_answer_phrase(judge, answer, "city2", "Austell")
    check_answer_phrase(judge, answer, "city3", "East Point")
    check_answer_phrase(judge, answer, "city4", "Lawrenceville")
    check_answer_phrase(judge, answer, "city5", "Marietta")
    check_answer_phrase(judge, answer, "city6", "Mcdonough")

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
