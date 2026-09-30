#!/usr/bin/env python3
"""Deterministic verifier for Disney--6 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent,
    check_answer_any,
    check_answer_count_at_least,
    check_answer_number,
    check_answer_number_absent,
    check_answer_ordered,
    check_answer_phrase,
    check_answer_regex,
    check_only_tables_changed,
    check_read_only,
    check_row_matches,
    check_rows_added,
    check_screenshots,
    check_seed_contract,
    check_trajectory_identity,
    check_visited_all,
    check_visited_any,
    check_visited_path,
    run_verifier
)

TASK_ID = "Disney--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "mk_thrill", r"""/parks/attractions\?[^\" ]*park=magic-kingdom[^\" ]*interest=Thrill\+Rides|/parks/attractions\?[^\" ]*interest=Thrill\+Rides[^\" ]*park=magic-kingdom"""),
    check_visited_path(judge, traj, "mk_thrill_40", r"""/parks/attractions\?[^\" ]*height=40"""),
    check_visited_path(judge, traj, "first_detail", r"""/parks/attractions/magic-kingdom/space-mountain"""),
    check_visited_path(judge, traj, "mk_thrill_48", r"""/parks/attractions\?[^\" ]*height=48"""),
    check_visited_path(judge, traj, "tron_detail", r"""/parks/attractions/magic-kingdom/tron-lightcycle-run"""),
    check_visited_path(judge, traj, "mk_entertainment", r"""/parks/attractions\?[^\" ]*type=Entertainment"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "mk_thrill_count", 5)
    check_answer_number(judge, answer, "mk_thrill_40_count", 3)
    check_answer_phrase(judge, answer, "first_name", "Space Mountain")
    check_answer_phrase(judge, answer, "first_height", "44\" or taller")
    check_answer_any(judge, answer, "first_interest", ["Big Drops", "Dark", "Thrill Rides", "Adults"])
    check_answer_number(judge, answer, "mk_thrill_again", 5)
    check_answer_number(judge, answer, "h48_count", 1)
    check_answer_phrase(judge, answer, "h48_name", "TRON Lightcycle / Run")
    check_answer_number(judge, answer, "mk_entertainment_count", 26)

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
