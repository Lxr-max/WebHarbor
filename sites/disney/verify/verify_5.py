#!/usr/bin/env python3
"""Deterministic verifier for Disney--5 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    Known defect (pinned): the DuckTales rating answer is stable (both
    same-titled shows are TV-Y7) but the release year is not (1987/2017);
    this task only asks for the rating, which stays deterministic.

Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "shows_all", r"""/shows"""),
    check_visited_path(judge, traj, "shows_comedy", r"""/shows\?[^\" ]*genre=Comedy"""),
    check_visited_path(judge, traj, "shows_fantasy", r"""/shows\?[^\" ]*genre=Fantasy"""),
    check_visited_path(judge, traj, "fantasy_first_detail", r"""/shows/adventures-of-the-gummi-bears"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "duck_search", r"""/shows\?[^\" ]*q=duck"""),
    check_visited_any(judge, traj, "ducktales_detail", [r"""/shows/ducktales-products""", r"""/shows/ducktales$|/shows/ducktales\?"""]),
    check_visited_path(judge, traj, "comedy_title_sort", r"""/shows\?[^\" ]*genre=Comedy[^\" ]*sort=title|/shows\?[^\" ]*sort=title[^\" ]*genre=Comedy"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "shows_total", 54)
    check_answer_number(judge, answer, "comedy_count", 25)
    check_answer_number(judge, answer, "fantasy_count", 9)
    check_answer_phrase(judge, answer, "first_fantasy", "Adventures of the Gummi Bears")
    check_answer_number(judge, answer, "fantasy_year", 1985)
    check_answer_number(judge, answer, "duck_count", 3)
    check_answer_phrase(judge, answer, "duck_rating", "TV-Y7")
    check_answer_phrase(judge, answer, "first_comedy", "Austin & Ally")
    check_answer_phrase(judge, answer, "comedy_rating", "TV-G")

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=2 AND item_type='show' AND item_key='adventures-of-the-gummi-bears'",
        (), "bob_faved_gummi_bears")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
