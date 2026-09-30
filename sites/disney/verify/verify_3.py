#!/usr/bin/env python3
"""Deterministic verifier for Disney--3 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the task now says "clear the search and the genre filter,
    open the newer DuckTales series" — the two same-titled shows (1987
    original / 2017 reboot) make "newer" deterministic: the 2017 reboot
    at /shows/ducktales (TV-Y7). The agent must clear the still-active
    Science Fiction genre filter to see the card.

Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "shows_animation", r"""/shows\?[^\" ]*genre=Animation"""),
    check_visited_path(judge, traj, "shows_scifi", r"""/shows\?[^\" ]*genre=Science\+Fiction"""),
    check_visited_path(judge, traj, "shows_star_search", r"""/shows\?[^\" ]*q=star"""),
    check_visited_path(judge, traj, "first_star_detail", r"""/shows/lego-star-wars-droid-tales"""),
    check_visited_path(judge, traj, "shows_cleared", r"""/shows\?[^\" ]*genre=&"""),
    check_visited_any(judge, traj, "ducktales_detail", [r"""/shows/ducktales$"""]),
    check_visited_path(judge, traj, "bh6_detail", r"""/shows/big-hero-6-the-series"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "animation_count", 25)
    check_answer_number(judge, answer, "scifi_count", 10)
    check_answer_number(judge, answer, "star_count", 2)
    check_answer_phrase(judge, answer, "first_star_title", "LEGO Star Wars: Droid Tales")
    check_answer_number(judge, answer, "first_star_year", 2015)
    check_answer_phrase(judge, answer, "duck_rating", "TV-Y7")
    check_answer_number(judge, answer, "duck_year", 2017)
    check_answer_phrase(judge, answer, "bh6_title", "Big Hero 6: The Series")
    check_answer_phrase(judge, answer, "bh6_rating", "TV-Y7")
    check_answer_number(judge, answer, "bob_favorites_total", 4)
    check_answer_number(judge, answer, "bob_shows_saved", 3)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=2 AND item_type='show' AND item_key='big-hero-6-the-series'",
        (), "bob_faved_bh6")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
