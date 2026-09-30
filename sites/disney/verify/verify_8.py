#!/usr/bin/env python3
"""Deterministic verifier for Disney--8 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "attractions_all", r"""/parks/attractions\?[^\" ]*type=Attraction"""),
    check_visited_path(judge, traj, "h38", r"""/parks/attractions\?[^\" ]*height=38"""),
    check_visited_path(judge, traj, "h44", r"""/parks/attractions\?[^\" ]*height=44"""),
    check_visited_path(judge, traj, "h48", r"""/parks/attractions\?[^\" ]*height=48"""),
    check_visited_path(judge, traj, "height_sort", r"""/parks/attractions\?[^\" ]*sort=height"""),
    check_visited_path(judge, traj, "first_detail", r"""/parks/attractions/blizzard-beach/downhill-double-dipper"""),
    check_visited_path(judge, traj, "last_detail", r"""/parks/attractions/magic-kingdom/tron-lightcycle-run"""),
    check_visited_path(judge, traj, "big_drops", r"""/parks/attractions\?[^\" ]*interest=Big\+Drops"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "attractions_total", 160)
    check_answer_number(judge, answer, "h38_count", 22)
    check_answer_number(judge, answer, "h44_count", 8)
    check_answer_number(judge, answer, "h48_count", 5)
    check_answer_phrase(judge, answer, "first_name", "Downhill Double Dipper")
    check_answer_phrase(judge, answer, "first_park", "Disney's Blizzard Beach Water Park")
    check_answer_phrase(judge, answer, "last_name", "TRON Lightcycle / Run")
    check_answer_phrase(judge, answer, "last_park", "Magic Kingdom Park")
    check_answer_number(judge, answer, "attractions_total_again", 160)
    check_answer_number(judge, answer, "big_drops_count", 8)

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
