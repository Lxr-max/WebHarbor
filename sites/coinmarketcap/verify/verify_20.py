#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--20 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_20.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--20"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_btc", r"/currencies/bitcoin/")
    check_visited_all(judge, traj, "nav_btc_ranges",
                      [r"range=1D", r"range=7D", r"range=1M", r"range=3M",
                       r"range=1Y", r"range=YTD", r"range=All"])
    check_answer_phrase(judge, answer, "btc_1d_high", "$84,421.61")
    check_answer_phrase(judge, answer, "btc_7d_high", "$86,871.64")
    check_answer_phrase(judge, answer, "btc_1m_high", "$86,945.23")
    check_answer_phrase(judge, answer, "btc_3m_high", "$86,130.69")
    check_answer_phrase(judge, answer, "btc_1y_high", "$123,510.45")
    check_answer_phrase(judge, answer, "btc_ytd_high", "$96,460.42")
    check_answer_phrase(judge, answer, "btc_all_high", "$115,399.63")
    check_answer_phrase(judge, answer, "btc_52w_low", "$57,747.76")
    check_answer_phrase(judge, answer, "btc_52w_high", "$126,198.07")
    check_visited_path(judge, traj, "nav_eth", r"/currencies/ethereum/")
    check_visited_all(judge, traj, "nav_eth_ranges", [r"range=7D", r"range=1M", r"range=1Y", r"range=All"])
    check_answer_phrase(judge, answer, "eth_all_high", "$4,503.64")
    check_visited_path(judge, traj, "nav_sol", r"/currencies/solana/")
    check_answer_phrase(judge, answer, "sol_52w_low", "$60.41")
    check_answer_phrase(judge, answer, "sol_52w_high", "$237.32")
    check_visited_path(judge, traj, "nav_doge", r"/currencies/dogecoin/")
    check_visited_path(judge, traj, "nav_xrp", r"/currencies/xrp/")
    check_answer_phrase(judge, answer, "xrp_7d", "-5.21%")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
