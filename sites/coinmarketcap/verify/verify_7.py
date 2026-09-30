#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--7 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_watchlist", r"/watchlist/")
    check_visited_path(judge, traj, "nav_doge", r"/currencies/dogecoin/")
    check_answer_phrase(judge, answer, "alice_btc_price", "$83,622.87")
    check_answer_phrase(judge, answer, "alice_eth_price", "$2,677.00")
    check_answer_phrase(judge, answer, "alice_sol_price", "$119.03")
    check_answer_phrase(judge, answer, "alice_btc_24h", "+0.12%")
    check_answer_phrase(judge, answer, "alice_eth_24h", "-0.47%")
    check_answer_phrase(judge, answer, "alice_sol_24h", "+0.20%")
    check_answer_phrase(judge, answer, "doge_price", "$0.0938504")
    check_answer_phrase(judge, answer, "final_btc", "Bitcoin")
    check_answer_phrase(judge, answer, "final_sol", "Solana")
    check_answer_phrase(judge, answer, "final_doge", "Dogecoin")
    check_answer_phrase(judge, answer, "wrong_pw_error",
                        "Your email and password does not match. Please try again.")
    check_only_tables_changed(judge, initial, after, {"watchlist_items"})
    check_rows_removed(judge, initial, after, "watchlist_items",
                       [(None, 1, 1027, None)], "wl_removed_eth_alice")
    check_rows_added(judge, initial, after, "watchlist_items",
                     [(None, 1, 74, None)], "wl_added_doge_alice")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
