#!/usr/bin/env python3
"""Deterministic verifier for Disney--4 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the site-wide search now lists full result sets, so the
    printed Parks & Entertainment count is the true match count (13;
    was capped at 12 with the r1 mirror).

Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "mickey_search", r"""/search\?[^\" ]*q=mickey"""),
    check_visited_path(judge, traj, "mm_detail", r"""/shows/disney-mickey-mouse"""),
    check_visited_path(judge, traj, "shows_variety", r"""/shows\?[^\" ]*genre=Variety"""),
    check_visited_path(judge, traj, "variety_first_detail", r"""/shows/disney-mickey-mouse"""),
    check_visited_path(judge, traj, "shows_all", r"""/shows\?[^\" ]*genre=&|/shows$|/shows\?"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    check_visited_path(judge, traj, "duck_search", r"""/shows\?[^\" ]*q=duck"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "mickey_shows", 2)
    check_answer_number(judge, answer, "mickey_parks_entertainment", 13)
    check_answer_phrase(judge, answer, "mm_rating", "TV-G")
    check_answer_number(judge, answer, "variety_count", 3)
    check_answer_number(judge, answer, "shows_total", 54)
    check_answer_number(judge, answer, "carol_favorites_total", 3)
    check_answer_number(judge, answer, "duck_count", 3)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=3 AND item_type='show' AND item_key='disney-mickey-mouse'",
        (), "carol_faved_mickey_mouse")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
