#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--14 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note (B3 depth): the task was deepened (T14 honest depth 13→16 atomic
steps) with one more text-required surface — XRP's Markets page for its top
pair and volume (XRP/USDT on Binance, $288.20M).
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_btc_markets", r"/currencies/bitcoin/markets/")
    check_visited_path(judge, traj, "nav_eth_markets", r"/currencies/ethereum/markets/")
    check_visited_path(judge, traj, "nav_doge_markets", r"/currencies/dogecoin/markets/")
    check_visited_path(judge, traj, "nav_xrp_markets", r"/currencies/xrp/markets/")
    check_visited_path(judge, traj, "nav_sol_markets", r"/currencies/solana/markets/")
    check_visited_path(judge, traj, "nav_binance", r"/exchanges/binance/")
    check_answer_phrase(judge, answer, "btc_pair1", "BTC/USDT")
    check_answer_phrase(judge, answer, "btc_pair1_volume", "$1.11B")
    check_answer_phrase(judge, answer, "btc_pair2", "BTC/USDC")
    check_answer_phrase(judge, answer, "btc_pair3", "BTC/USD")
    check_answer_phrase(judge, answer, "btc_usdt_top_exchange", "Binance")
    check_answer_phrase(judge, answer, "eth_pair", "ETH/USDT")
    check_answer_phrase(judge, answer, "eth_exchange", "Binance")
    check_answer_phrase(judge, answer, "doge_pair", "DOGE/USDT")
    check_answer_phrase(judge, answer, "doge_volume", "$64.35M")
    check_answer_phrase(judge, answer, "xrp_pair", "XRP/USDT")
    check_answer_phrase(judge, answer, "xrp_volume", "$288.20M")
    check_answer_phrase(judge, answer, "sol_exchange", "Binance")
    check_answer_phrase(judge, answer, "binance_fees", "0.02% / 0.04%")
    check_answer_phrase(judge, answer, "binance_top_pair", "USDC/USDT")
    check_answer_phrase(judge, answer, "btc_market_score", "9.9783")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
