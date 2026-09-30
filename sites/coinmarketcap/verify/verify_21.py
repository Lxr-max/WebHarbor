#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--21 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_21.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--21"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_watchlist", r"/watchlist/")
    check_answer_phrase(judge, answer, "bob_xrp", "XRP")
    check_answer_phrase(judge, answer, "bob_doge", "Dogecoin")
    check_answer_phrase(judge, answer, "bob_ada", "Cardano")
    check_answer_phrase(judge, answer, "alice_sol", "Solana")
    check_answer_phrase(judge, answer, "alice_doge_absent", "no")
    check_answer_phrase(judge, answer, "chainlink_added", "Chainlink")
    check_answer_phrase(judge, answer, "link_price", "$14.60")
    check_answer_phrase(judge, answer, "guest_prompt",
                        "Wanna keep this Watchlist? Just sign up in a few easy steps!")
    check_answer_phrase(judge, answer, "guest_coin", "Cardano")
    check_only_tables_changed(judge, initial, after, {"watchlist_items"})
    check_rows_added(judge, initial, after, "watchlist_items",
                     [(None, 2, 1975, None)], "wl_added_link_bob")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
