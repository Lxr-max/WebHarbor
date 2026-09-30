#!/usr/bin/env python3
"""Deterministic verifier for Disney--2 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the task now says "open the first result" for the
    release-date sort (the r1 wording "most recently released" was
    ambiguous); the anchor is unchanged — the top of the release sort is
    Star Wars: Starfighter (May 28, 2027, Not Yet Rated).

Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "movies_star_search", r"""/movies\?[^\" ]*q=star"""),
    check_visited_path(judge, traj, "cs_scifi", r"""/movies\?[^\" ]*status=coming_soon[^\" ]*genre=Science\+Fiction|/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*status=coming_soon"""),
    check_visited_path(judge, traj, "doomsday_detail", r"""/movies/avengers-doomsday"""),
    check_visited_path(judge, traj, "scifi_release_sort", r"""/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*sort=release|/movies\?[^\" ]*sort=release[^\" ]*genre=Science\+Fiction"""),
    check_visited_path(judge, traj, "newest_detail", r"""/movies/star-wars-starfighter"""),
    check_visited_path(judge, traj, "scifi_title_sort", r"""/movies\?[^\" ]*genre=Science\+Fiction[^\" ]*sort=title|/movies\?[^\" ]*sort=title[^\" ]*genre=Science\+Fiction"""),
    check_visited_path(judge, traj, "first_scifi_detail", r"""/movies/avatar-fire-and-ash"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "star_count", 2)
    check_answer_number(judge, answer, "cs_scifi_count", 2)
    check_answer_phrase(judge, answer, "first_cs_scifi_date", "December 18, 2026")
    check_answer_phrase(judge, answer, "newest_title", "Star Wars: Starfighter")
    check_answer_phrase(judge, answer, "newest_rating", "Not Yet Rated")
    check_answer_phrase(judge, answer, "newest_date", "May 28, 2027")
    check_answer_phrase(judge, answer, "title_first", "Avatar: Fire and Ash")
    check_answer_phrase(judge, answer, "title_first_rating", "PG-13")
    check_answer_any(judge, answer, "cast_member", ["Sam Worthington", "Zoe Saldaña", "Sigourney Weaver", "Stephen Lang", "Oona Chaplin", "Cliff Curtis", "David Thewlis", "Giovanni Ribisi", "Kate Winslet"])

    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
