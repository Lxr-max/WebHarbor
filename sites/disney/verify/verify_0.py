#!/usr/bin/env python3
"""Deterministic verifier for Disney--0 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "movies_streaming", r"""/movies\?[^\" ]*status=streaming"""),
    check_visited_path(judge, traj, "first_streaming_detail", r"""/movies/avatar-the-way-of-water"""),
    check_visited_path(judge, traj, "movies_coming_soon", r"""/movies\?[^\" ]*status=coming_soon"""),
    check_visited_path(judge, traj, "first_cs_detail", r"""/movies/avengers-doomsday"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "streaming_count", 6)
    check_answer_phrase(judge, answer, "first_title", "Avatar: The Way of Water")
    check_answer_phrase(judge, answer, "rating", "PG-13")
    check_answer_phrase(judge, answer, "runtime", "3h 12min")
    check_answer_number(judge, answer, "coming_soon_count", 9)
    check_answer_phrase(judge, answer, "cs_release_date", "December 18, 2026")
    check_answer_number(judge, answer, "alice_favorites_total", 4)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=1 AND item_type='movie' AND item_key='avengers-doomsday'",
        (), "alice_faved_avengers_doomsday")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
