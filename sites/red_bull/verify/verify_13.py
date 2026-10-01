#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--13 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Red Bull--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/account/login$",
        r"/account$",
        r"/shows/inside-pro-surfing$",
        r"/events\?[^ ]*page=2",
        r"/events/red-bull-barn-find-open$",
        r"/stories/jreamz-wins-2026-red-bull-dance-your-style-national",
    ])
    check_answer_phrase(judge, answer, "bob_code", "RB2B8E90")
    check_answer_phrase(judge, answer, "bob_event", "Barn Find Open")
    check_answer_phrase(judge, answer, "bob_date", "October 17, 2026")
    check_answer_phrase(judge, answer, "bob_ticket", "registration")
    check_answer_phrase(judge, answer, "barn_venue", "Oak Ridge MX Track, Garwin, IA")
    check_answer_any(judge, answer, "story_topic", ["dance", "Dance", "DANCE"])
    check_only_tables_changed(judge, initial, after, {"favorites"})
    check_rows_removed(judge, initial, after, "favorites", [
        [None, 2, "show", "inside-pro-surfing"],
    ], "show_unfavorited")
    check_rows_added(judge, initial, after, "favorites", [
        [None, 2, "event", "red-bull-barn-find-open"],
    ], "event_favorited")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
