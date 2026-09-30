#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--6 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_mv", r"/most-viewed-pages/")
    check_visited_path(judge, traj, "nav_star1", r"/currencies/asentum/")
    check_visited_path(judge, traj, "nav_star_btc", r"/currencies/bitcoin/")
    check_visited_path(judge, traj, "nav_watchlist", r"/watchlist/")
    check_visited_path(judge, traj, "nav_signup", r"/signup")
    check_answer_phrase(judge, answer, "prompt",
                        "Wanna keep this Watchlist? Just sign up in a few easy steps!")
    check_answer_phrase(judge, answer, "coin1", "Bitcoin")
    check_answer_phrase(judge, answer, "coin1_price", "$83,622.87")
    check_answer_phrase(judge, answer, "coin2", "Asentum")
    check_answer_phrase(judge, answer, "coin2_price", "$0.00181026")
    check_answer_regex(judge, answer, "greeting", r"Hi,\s*\w+")
    check_answer_phrase(judge, answer, "survived_bitcoin", "Bitcoin")
    check_answer_phrase(judge, answer, "survived_asentum", "Asentum")
    check_answer_phrase(judge, answer, "removed_bitcoin_remaining", "Asentum")
    check_only_tables_changed(judge, initial, after, {"users", "watchlist_items"})
    check_rows_added(judge, initial, after, "users",
                     [(None, 'rx:.+@.+[.].+',
                       None, None, 0, "2026-09-29")], "users_added")
    # guest carry-over adds Asentum (coin id 39920) + Bitcoin (id 1) at
    # signup, then the task's remove-Bitcoin step deletes the id-1 row
    # again, so the net after-state delta is one watchlist row, zero removals.
    check_rows_added(judge, initial, after, "watchlist_items",
                     [(None, 5, 39920, None)], "wl_added_asentum_carried")
    check_rows_removed(judge, initial, after, "watchlist_items", [],
                       "wl_no_seed_removals")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
