#!/usr/bin/env python3
"""Deterministic verifier for Disney--19 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the parks hub now shows real display names for all locations
    (no bare slugs; listed count 10 and EPCOT's 72 unaffected), and the
    favorites toggle stores the full park/slug key so Carol's favorited
    card renders on /favorites (count == rendered cards == 3).

Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "parks_hub", r"""/parks($|\?)"""),
    check_visited_path(judge, traj, "epcot_attractions", r"""/parks/attractions\?[^\" ]*park=epcot[^\" ]*type=Attraction|/parks/attractions\?[^\" ]*type=Attraction[^\" ]*park=epcot"""),
    check_visited_path(judge, traj, "first_detail", r"""/parks/attractions/epcot/mission-space-advanced-training-lab"""),
    check_visited_path(judge, traj, "epcot_charexp", r"""/parks/attractions\?[^\" ]*park=epcot[^\" ]*type=Entertainment[^\" ]*interest=Character\+Experiences"""),
    check_visited_path(judge, traj, "charexp_detail", r"""/parks/attractions/epcot/visa-card-character-experience"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "parks_listed", 10)
    check_answer_phrase(judge, answer, "most_park", "EPCOT")
    check_answer_number(judge, answer, "most_park_count", 72)
    check_answer_number(judge, answer, "epcot_attractions_count", 41)
    check_answer_phrase(judge, answer, "first_attraction", "Advanced Training Lab")
    check_answer_phrase(judge, answer, "first_height", "Any height")
    check_answer_number(judge, answer, "epcot_charexp_count", 15)
    check_answer_phrase(judge, answer, "first_charexp", "Disney® Visa® Cardmember Photo Opportunity at EPCOT")
    check_answer_number(judge, answer, "carol_favorites_total", 3)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=3 AND item_type='attraction' AND item_key='epcot/visa-card-character-experience'",
        (), "carol_faved_visa_charexp")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
