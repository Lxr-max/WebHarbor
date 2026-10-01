#!/usr/bin/env python3
"""Deterministic verifier for University of Michigan--14 (university_of_michigan).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-umich-review-r2, seed md5
0492574f8c28ddc5b923294839d99cc0, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "University of Michigan--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Most recent story ('Abuse and disability trap: 90% of incarcerated
    # Michigan youth suffered prior abuse'); arts-culture (4); 'Arts taking
    # center stage' (2026-09-25, festival kicks off October); r2 fix: site
    # search for 'El Niño' (the real spelling) returns the story (variability
    # nearly 40% stronger); health most recent (Arts taking center stage);
    # bob login; Bob's first Backpack class (ECON 101, Adam Stevenson) opened
    # from My U-M.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/news\?category=arts-culture",
        r"/news/arts-taking-center-stage",
        r"/search\?q=El",
        r"/news/el-ninos-more-intense",
        r"/news\?category=health",
        r"/login",
        r"/myumich",
        r"/courses/class/10918",
    ])
    check_answer_phrase(judge, answer, "most_recent_title", "Abuse and disability trap")
    check_answer_number(judge, answer, "arts_count", 4)
    check_answer_phrase(judge, answer, "arts_story_date", "2026-09-25")
    check_answer_phrase(judge, answer, "arts_festival_month", "October")
    check_answer_regex(judge, answer, "el_nino_strength", r"40\s?%|forty percent")
    check_answer_phrase(judge, answer, "health_recent_title", "Arts taking center stage")
    check_answer_phrase(judge, answer, "bob_first_backpack_course", "ECON 101")
    check_answer_phrase(judge, answer, "bob_first_backpack_instructor", "Adam Stevenson")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
