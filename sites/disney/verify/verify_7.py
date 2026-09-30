#!/usr/bin/env python3
"""Deterministic verifier for Disney--7 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the task now names "the Heartbeat of Freedom fireworks
    show at EPCOT" (two EPCOT fireworks exist; the name is
    deterministic), and the favorites toggle now stores the full
    park/slug key with the card rendering on /favorites (count ==
    rendered cards == 4).

Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "char_exp_all", r"""/parks/attractions\?[^\" ]*type=Entertainment[^\" ]*interest=Character\+Experiences|/parks/attractions\?[^\" ]*interest=Character\+Experiences[^\" ]*type=Entertainment"""),
    check_visited_path(judge, traj, "char_exp_mk", r"""/parks/attractions\?[^\" ]*park=magic-kingdom"""),
    check_visited_path(judge, traj, "mk_first_detail", r"""/parks/attractions/magic-kingdom/starlight-dream-night-away-parade"""),
    check_visited_path(judge, traj, "fireworks", r"""/parks/attractions\?[^\" ]*interest=Fireworks"""),
    check_visited_path(judge, traj, "login", r"""/login"""),
    check_visited_path(judge, traj, "favorites", r"""/favorites"""),
    check_visited_path(judge, traj, "epcot_fireworks_detail", r"""/parks/attractions/epcot/heartbeat-of-freedom"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "char_exp_all_count", 44)
    check_answer_number(judge, answer, "char_exp_mk_count", 12)
    check_answer_phrase(judge, answer, "mk_first_name", "Disney Starlight: Dream the Night Away")
    check_answer_number(judge, answer, "fireworks_count", 6)
    check_answer_number(judge, answer, "alice_favorites_total", 4)

    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_added(judge, initial, after, "favorites", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM favorites WHERE user_id=1 AND item_type='attraction' "
        "AND item_key='epcot/heartbeat-of-freedom'",
        (), "alice_faved_heartbeat_of_freedom")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
