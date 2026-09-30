#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--4 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Backcountry--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cat", r"/cat/climb")
    check_visited_path(judge, traj, "nav_sorted", r"/cat/climb\?sort=-rating")
    check_visited_path(judge, traj, "nav_pdp_momentum", r"black-diamond-momentum-climbing-shoe-mens")
    check_visited_path(judge, traj, "nav_pdp_second", r"la-sportiva-tarantulace-climbing-shoe")
    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_pdp_review", r"black-diamond-momentum-climbing-shoe-mens\?review-posted=1|black-diamond-momentum-climbing-shoe-mens")
    check_answer_phrase(judge, answer, "title", "Momentum Climbing Shoe - Men's")
    check_answer_phrase(judge, answer, "rating", '4.5')
    check_answer_number(judge, answer, "reviews", 244)
    check_answer_money(judge, answer, "sale", 69.97)
    check_answer_money(judge, answer, "list", 99.95)
    check_answer_phrase(judge, answer, "second", 'Tarantulace Climbing Shoe')
    check_answer_number(judge, answer, "after_count", 245)
    check_only_tables_changed(judge, initial, after, {"reviews"})
    check_rows_added(judge, initial, after, "reviews",
                      [[None, None, "BLD00QS", 3, "Carol Davis", "Edges like a dream", "Stuck to overhangs all session and never once slipped.", 4, "rx:2026-09-30", "I've used it several times", None, None, "[]", 0, None, 0, 0]], "review_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
