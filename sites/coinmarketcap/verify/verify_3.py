#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--3 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix notes (B2 + H2 + depth, all resolved in this revision):
  1. The historical-data days tabs FILTER now (the route applies the days
     window: the `days` most recent daily rows), so the row counts are 7 / 90 /
     365 instead of the r1 full-capture 365/365.
  2. The chart's plotted maximum is marked and labeled with its date, so
     "the highest price in the All range with its date" is derivable from the
     page: $115,399.63 on Sep 15, 2025 (the ATH metric $126,198.07 · Oct 06,
     2025 remains a separate, still-correct metric gate).
  3. The task was deepened (T3 honest depth 13→16 atomic steps): the chart
     range list now includes 3M and YTD, and the historical switch covers
     7/90/365 days.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_btc", r"/currencies/bitcoin/")
    check_visited_all(judge, traj, "nav_chart_ranges",
                      [r"range=1D", r"range=7D", r"range=1M", r"range=3M",
                       r"range=1Y", r"range=YTD", r"range=All"])
    check_visited_path(judge, traj, "nav_hist", r"/currencies/bitcoin/historical-data/")
    check_visited_path(judge, traj, "nav_hist_7", r"days=7")
    check_visited_path(judge, traj, "nav_hist_90", r"days=90")
    check_visited_path(judge, traj, "nav_hist_365", r"days=365")
    check_visited_path(judge, traj, "nav_markets", r"/currencies/bitcoin/markets/")
    check_answer_phrase(judge, answer, "btc_price", "$83,622.87")
    check_answer_phrase(judge, answer, "btc_24h", "+0.12%")
    check_answer_phrase(judge, answer, "btc_mcap", "$1.68T")
    check_answer_phrase(judge, answer, "btc_fdv", "$1.76T")
    check_answer_phrase(judge, answer, "btc_supply", "20,090,909")
    check_answer_phrase(judge, answer, "btc_max_supply", "21,000,000")
    check_answer_phrase(judge, answer, "all_range_high", "$115,399.63")
    check_answer_phrase(judge, answer, "all_range_high_date", "Sep 15, 2025")
    check_answer_phrase(judge, answer, "hist_recent_date", "2026-09-29")
    check_answer_phrase(judge, answer, "hist_recent_close", "$83,622.43")
    check_answer_number(judge, answer, "hist_7d_rows", 7)
    check_answer_number(judge, answer, "hist_90d_rows", 90)
    check_answer_number(judge, answer, "hist_365d_rows", 365)
    check_answer_phrase(judge, answer, "markets_top_pair", "BTC/USDT")
    check_answer_phrase(judge, answer, "markets_top_exchange", "Binance")
    check_answer_phrase(judge, answer, "markets_top_price", "$83,540.61")
    check_answer_phrase(judge, answer, "markets_top_volume", "$1.11B")
    check_answer_phrase(judge, answer, "ath", "$126,198.07")
    check_answer_phrase(judge, answer, "ath_date", "Oct 06, 2025")
    check_answer_phrase(judge, answer, "ath_pct", "-33.74%")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
