#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--12 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Podcast page facts; home podcast section; pumpkin pie spice; alice add + list ops.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/podcast",
        r"/home/search\?q=pumpkin\+pie\+spice",
        r"/home/products/pdp/084771",
        r"/login",
        r"/home/shopping-list",
    ])
    check_answer_phrase(judge, answer, "newest_episode", "Episode 112: Time for Tacos at Trader Joe's")
    check_answer_phrase(judge, answer, "newest_date", "21 Sep 2026")
    check_answer_phrase(judge, answer, "second_newest",
                        "Episode 111: Can't Help Falling for this Trader Joe's Shopping List")
    check_answer_number(judge, answer, "episodes_table_count", 12)
    check_answer_phrase(judge, answer, "home_podcast_section", "Podcast")
    check_answer_phrase(judge, answer, "pps_title", "Pumpkin Pie Spice Bark")
    check_answer_price(judge, answer, "pps_price", 5.49)
    check_answer_phrase(judge, answer, "pps_size", "8 Oz")
    check_answer_number(judge, answer, "new_total", 9)
    check_answer_number(judge, answer, "bisque_qty", 3)
    check_answer_number(judge, answer, "total_after_increase", 10)
    check_answer_number(judge, answer, "total_after_remove", 9)
    check_only_tables_changed(judge, initial, after, {"shopping_items"})
    # the task adds and then removes the pumpkin pie spice within the same
    # session: the net add/remove deltas are both empty (pinned below so an
    # agent that leaves the spice in the list cannot fake it)
    check_rows_added(judge, initial, after, "shopping_items",
                     [], "spice_add_remove_net_zero")
    check_rows_changed(judge, initial, after, "shopping_items",
                       [[4, 1, "067075", 4, None]], "increase_pumpkin_bisque")
    check_rows_removed(judge, initial, after, "shopping_items",
                       [], "spice_add_remove_net_zero_removed")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
