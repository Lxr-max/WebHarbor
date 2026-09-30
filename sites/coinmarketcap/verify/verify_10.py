#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--10 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note (B3 depth): the task was deepened (T10 honest depth 11→17
atomic steps) with three more text-required exchange pages — Bybit, KuCoin
and MEXC, each with a real fee question — so the navigation gate now covers
eight spot exchange pages.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_rankings", r"/rankings/exchanges/")
    check_visited_all(judge, traj, "nav_exchanges",
                      [r"/exchanges/binance/", r"/exchanges/coinbase-exchange/",
                       r"/exchanges/kraken/", r"/exchanges/upbit/", r"/exchanges/okx/",
                       r"/exchanges/bybit/", r"/exchanges/kucoin/", r"/exchanges/mexc/"])
    check_answer_ordered(judge, answer, "spot_top3", ["Binance", "Coinbase Exchange", "Kraken"])
    check_answer_phrase(judge, answer, "binance_volume", "$11.14B")
    check_answer_phrase(judge, answer, "binance_share", "6.46%")
    check_answer_phrase(judge, answer, "coinbase_volume", "$2.26B")
    check_answer_phrase(judge, answer, "coinbase_share", "1.31%")
    check_answer_phrase(judge, answer, "kraken_volume", "$2.03B")
    check_answer_phrase(judge, answer, "kraken_share", "1.18%")
    check_answer_phrase(judge, answer, "binance_maker", "0.02%")
    check_answer_phrase(judge, answer, "binance_taker", "0.04%")
    check_answer_phrase(judge, answer, "binance_launch", "Jul 14, 2017")
    check_answer_number(judge, answer, "binance_coins", 882)
    check_answer_number(judge, answer, "binance_markets", 2199)
    check_answer_phrase(judge, answer, "binance_top_pair", "USDC/USDT")
    check_answer_phrase(judge, answer, "binance_top_pair_volume", "$3.02B")
    check_answer_phrase(judge, answer, "coinbase_fees", "0.00% / 0.00%")
    check_answer_phrase(judge, answer, "kraken_fees", "0.02% / 0.05%")
    check_answer_number(judge, answer, "kraken_visits", 1086112)
    check_answer_phrase(judge, answer, "upbit_taker", "0.10%")
    check_answer_phrase(judge, answer, "okx_maker", "0.02%")
    check_answer_phrase(judge, answer, "bybit_fees", "0.02% / 0.06%")
    check_answer_phrase(judge, answer, "kucoin_fees", "0.02% / 0.06%")
    check_answer_phrase(judge, answer, "mexc_fees", "0.00% / 0.02%")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
