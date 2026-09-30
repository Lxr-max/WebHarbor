#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--8 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/shows$",
        r"/shows/winter-heroes$",
        r"/shows\?[^ ]*discipline=Snowboarding",
        r"/shows/glimpse$",
        r"/shows\?[^ ]*discipline=Surfing",
        r"/shows/no-contest-off-tour$",
        r"/shows/inside-pro-surfing$",
        r"/shows/all-day-sj-show$",
    ])
    check_answer_number(judge, answer, "wh_seasons", 1)
    check_answer_number(judge, answer, "wh_episodes", 15)
    check_answer_count_at_least(judge, answer, "wh_first3",
                                ["Eileen Gu", "Kjeld Nuis", "Queralt Castellet"], 3)
    check_answer_number(judge, answer, "snow_shows", 4)
    check_answer_phrase(judge, answer, "glimpse_sub", "Ride along with snowboarder Scotty James")
    check_answer_number(judge, answer, "glimpse_eps", 10)
    check_answer_phrase(judge, answer, "nc_discipline", "Surfing")
    check_answer_number(judge, answer, "nc_eps", 13)
    check_answer_number(judge, answer, "ips_seasons", 2)
    check_answer_number(judge, answer, "ips_episodes", 19)
    # r2 re-anchor: Inside Pro Surfing is opened explicitly (subheading)
    check_answer_phrase(judge, answer, "ips_sub", "Come backstage on the 2025 WSL Championship Tour")
    check_answer_phrase(judge, answer, "second_snow", "All Day SJ")
    check_answer_number(judge, answer, "second_snow_eps", 7)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
