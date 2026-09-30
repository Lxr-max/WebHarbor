#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--18 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

KNOWN-GAP (review finding): the home trending sidebar shows the
captured home-page trendingTopFive values (XDP +7.53%) while the Trending
page shows the captured unified-trending values (XDP +7.29%) — both are
real upstream captures from different endpoints; the task asks for the
sidebar value first and the page's platform/liquidity/txns after.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_answer_phrase(judge, answer, "stats_mcap", "$2.86T")
    check_answer_phrase(judge, answer, "stats_vol", "$91.41B")
    check_answer_phrase(judge, answer, "stats_btc_dom", "58.7%")
    check_answer_phrase(judge, answer, "stats_eth_dom", "11.4%")
    check_answer_phrase(judge, answer, "stats_gas", "0.13")
    check_answer_number(judge, answer, "stats_fg", 67)
    check_answer_regex(judge, answer, "stats_fg_label", r"Greed")
    check_answer_any(judge, answer, "stats_cryptos", ["62.27M", "62.26M"])
    check_answer_number(judge, answer, "stats_exchanges", 978)
    check_answer_phrase(judge, answer, "trend_sidebar_top", "Doppler Finance")
    check_answer_phrase(judge, answer, "trend_sidebar_24h", "+7.53%")
    check_visited_path(judge, traj, "nav_trending", r"/trending-cryptocurrencies/")
    check_answer_phrase(judge, answer, "trend_platform", "Base")
    check_answer_phrase(judge, answer, "trend_dex_liq", "$2.39M")
    check_answer_number(judge, answer, "trend_dex_txns", 689350)
    check_visited_path(judge, traj, "nav_trend1", r"/currencies/doppler-finance/")
    check_answer_number(judge, answer, "trend1_rank", 655)
    check_answer_phrase(judge, answer, "mv2", "Bitcoin")
    check_answer_phrase(judge, answer, "mv2_price", "$83,622.87")
    check_answer_phrase(judge, answer, "mv3", "Quant")
    check_answer_phrase(judge, answer, "mv3_price", "$266.71")
    check_answer_phrase(judge, answer, "mv4", "XRP")
    check_answer_phrase(judge, answer, "mv4_price", "$1.49")
    check_answer_phrase(judge, answer, "mv5", "Ethereum")
    check_answer_phrase(judge, answer, "mv5_price", "$2,677.00")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
