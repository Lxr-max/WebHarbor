#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--4 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_eth", r"/currencies/ethereum/")
    check_visited_path(judge, traj, "nav_sol", r"/currencies/solana/")
    check_visited_path(judge, traj, "nav_converter", r"/converter/")
    check_visited_path(judge, traj, "nav_doge", r"/currencies/dogecoin/")
    check_answer_phrase(judge, answer, "eth_price", "$2,677.00")
    check_answer_phrase(judge, answer, "eth_24h", "-0.47%")
    check_answer_phrase(judge, answer, "eth_mcap", "$326.83B")
    check_answer_phrase(judge, answer, "sol_price", "$119.03")
    check_answer_phrase(judge, answer, "sol_24h", "+0.20%")
    check_answer_phrase(judge, answer, "sol_mcap", "$69.97B")
    check_answer_money(judge, answer, "conv_2_5_btc", 209057.16)
    check_answer_money(judge, answer, "conv_0_1_btc", 8362.29)
    check_answer_money(judge, answer, "conv_1_btc_eth", 31.24)
    check_answer_money(judge, answer, "conv_3_eth", 8030.99)
    check_answer_money(judge, answer, "conv_10000_doge", 938.50)
    check_answer_phrase(judge, answer, "doge_price", "$0.0938504")
    check_answer_phrase(judge, answer, "doge_24h", "+0.01%")
    check_answer_number(judge, answer, "doge_watchers", 2267570)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
