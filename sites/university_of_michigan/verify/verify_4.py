#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--4 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_only_tables_changed,
    check_screenshots, check_seed_contract, check_trajectory_identity,
    check_visited_all, check_visited_any, check_visited_path, final_answer,
    run_verifier,
)

TASK_ID = "University of Michigan--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # News categories (health 5, arts-culture 4); arts first story
    # 'Arts taking center stage...' (2026-09-25); health most recent (same);
    # histotripsy search -> r2 de-leak: the foundation named among the
    # center's funding sources (Li Ka Shing Foundation — a body fact, NOT in
    # the search-result title); Well-being events (4), Lunchtime Yoga
    # 2026-09-18; dana counts (1 event, 1 program).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/news\?category=arts-culture",
        r"/news\?category=health",
        r"/search\?q=histotripsy",
        r"/news/10m-histotripsy",
        r"/events\?[^ ]*type=Well-being",
        r"/login",
        r"/myumich",
    ])
    check_answer_number(judge, answer, "health_count", 5)
    check_answer_number(judge, answer, "arts_count", 4)
    check_answer_phrase(judge, answer, "arts_first_title", "Arts taking center stage")
    check_answer_phrase(judge, answer, "arts_first_date", "2026-09-25")
    check_answer_phrase(judge, answer, "health_recent_title", "Arts taking center stage")
    check_answer_phrase(judge, answer, "histotripsy_foundation", "Li Ka Shing Foundation")
    check_answer_number(judge, answer, "wellbeing_count", 4)
    check_answer_phrase(judge, answer, "lunchtime_yoga_date", "2026-09-18")
    check_answer_number(judge, answer, "dana_saved_events", 1)
    check_answer_number(judge, answer, "dana_saved_programs", 1)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
