#!/usr/bin/env python3
"""Deterministic verifier for Disney--17 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: game titles are the clean hub names (no CMS artifacts), the
    availability line renders as a badge, and the description is real
    upstream rich text under a Description heading — the games search for
    'disney' now matches 3 of the 4 games (Gargoyles Remastered is clean).

Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "signup", r"""/signup"""),
    check_visited_path(judge, traj, "games", r"""/games"""),
    check_visited_path(judge, traj, "games_search", r"""/games\?[^\" ]*q=disney"""),
    check_visited_path(judge, traj, "illusion_detail", r"""/games/disney-illusion-island"""),
    check_visited_path(judge, traj, "cafe_detail", r"""/games/disney-villains-cursed-cafe"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "games_total", 4)
    check_answer_number(judge, answer, "disney_games_count", 3)
    check_answer_phrase(judge, answer, "illusion_title", "Disney Illusion Island")
    check_answer_phrase(judge, answer, "illusion_first_sentence", "Join Mickey & Friends on a quest to explore the mysterious island of Monoth and recover three mystical books to save the world from disaster!")
    check_answer_phrase(judge, answer, "cafe_title", "Disney Villains Cursed Café")
    check_answer_number(judge, answer, "favorites_total", 2)
    check_answer_phrase(judge, answer, "fav_one", "Disney Illusion Island")
    check_answer_phrase(judge, answer, "fav_two", "Disney Villains Cursed Café")

    check_only_tables_changed(judge, initial, after, {"users", "favorites"})
    check_rows_added(judge, initial, after, "users", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM users WHERE email='game.player@test.com' AND name='Game Player'",
        (), "game_account")
    check_rows_added(judge, initial, after, "favorites", 2)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites f JOIN users u ON f.user_id=u.id "
        "WHERE u.email='game.player@test.com' AND f.item_type='game' "
        "AND f.item_key IN ('disney-illusion-island', 'disney-villains-cursed-cafe')",
        (), "game_fav_1")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
