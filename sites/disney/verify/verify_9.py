#!/usr/bin/env python3
"""Deterministic verifier for Disney--9 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the favorites toggle now stores the full park/slug key,
    so Dana's favorited Soarin' card renders on /favorites (count ==
    rendered cards == 4).

Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "mk_thrill", r"""/parks/attractions\?[^\" ]*park=magic-kingdom[^\" ]*interest=Thrill\+Rides|/parks/attractions\?[^\" ]*interest=Thrill\+Rides[^\" ]*park=magic-kingdom"""),
    check_visited_path(judge, traj, "dwarfs_detail", r"""/parks/attractions/magic-kingdom/seven-dwarfs-mine-train"""),
    check_visited_path(judge, traj, "mk_dark", r"""/parks/attractions\?[^\" ]*interest=Dark"""),
    check_visited_path(judge, traj, "pirates_detail", r"""/parks/attractions/magic-kingdom/pirates-of-the-caribbean"""),
    check_visited_path(judge, traj, "related_detail", r"""/parks/attractions/magic-kingdom/pirates-adventures"""),
    check_visited_path(judge, traj, "epcot_slow", r"""/parks/attractions\?[^\" ]*park=epcot[^\" ]*interest=Slow\+Rides|/parks/attractions\?[^\" ]*interest=Slow\+Rides[^\" ]*park=epcot"""),
    check_visited_path(judge, traj, "soarin_detail", r"""/parks/attractions/epcot/soarin-around-world"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "mk_thrill_count", 5)
    check_answer_phrase(judge, answer, "dwarfs_height", "38\" or taller")
    check_answer_phrase(judge, answer, "dwarfs_heading", "Heigh-Ho, It's Off You Go!")
    check_answer_number(judge, answer, "mk_dark_count", 4)
    check_answer_phrase(judge, answer, "pirates_park", "Magic Kingdom Park")
    check_answer_phrase(judge, answer, "related_name", "A Pirate's Adventure ~ Treasures of the Seven Seas")
    check_answer_phrase(judge, answer, "related_park", "Magic Kingdom Park")
    check_answer_number(judge, answer, "epcot_slow_count", 9)
    check_answer_phrase(judge, answer, "soarin_park", "EPCOT")
    check_answer_number(judge, answer, "dana_favorites_total", 4)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=4 AND item_type='attraction' AND item_key='epcot/soarin-around-world'",
        (), "dana_faved_soarin")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
