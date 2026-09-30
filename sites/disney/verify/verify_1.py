#!/usr/bin/env python3
"""Deterministic verifier for Disney--1 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "signup", r"""/signup"""),
    check_visited_path(judge, traj, "movies_coming_soon", r"""/movies\?[^\" ]*status=coming_soon"""),
    check_visited_path(judge, traj, "cs_animation", r"""/movies\?[^\" ]*status=coming_soon[^\" ]*genre=Animation|/movies\?[^\" ]*genre=Animation[^\" ]*status=coming_soon"""),
    check_visited_path(judge, traj, "first_detail", r"""/movies/frozen-3"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "cs_count", 9)
    check_answer_number(judge, answer, "cs_animation_count", 6)
    check_answer_phrase(judge, answer, "first_title", "Frozen 3")
    check_answer_phrase(judge, answer, "release_date", "November 24, 2027")
    check_answer_phrase(judge, answer, "rating", "Not Yet Rated")
    check_answer_number(judge, answer, "moana_favorites_total", 1)
    check_answer_phrase(judge, answer, "fav_title", "Frozen 3")

    check_only_tables_changed(judge, initial, after, {"users", "favorites"})
    check_rows_added(judge, initial, after, "users", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM users WHERE email='moana.fan@test.com' AND name='Moana Fan'",
        (), "moana_account")
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites f JOIN users u ON f.user_id=u.id "
        "WHERE u.email='moana.fan@test.com' AND f.item_type='movie' AND f.item_key='frozen-3'",
        (), "moana_faved_frozen3")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
