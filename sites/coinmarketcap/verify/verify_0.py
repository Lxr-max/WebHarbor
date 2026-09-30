#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--0 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_sort_24h", r"sort=pct_24h")
    check_visited_path(judge, traj, "nav_top_gainer", r"/currencies/grass/")
    check_visited_path(judge, traj, "nav_sort_1h", r"sort=pct_1h")
    check_visited_path(judge, traj, "nav_1h_mover", r"/currencies/quant/")
    check_visited_path(judge, traj, "nav_sort_price", r"sort=price")
    check_visited_path(judge, traj, "nav_sort_volume", r"sort=volume_24h")
    check_visited_path(judge, traj, "nav_vol_top", r"/currencies/tether/")
    check_visited_path(judge, traj, "nav_markets", r"/currencies/tether/markets/")
    check_visited_path(judge, traj, "nav_page2", r"page=2")
    check_answer_phrase(judge, answer, "top_gainer", "Grass")
    check_answer_any(judge, answer, "top_gainer_sym", ["GRASS"])
    check_answer_phrase(judge, answer, "top_gainer_24h", "+29.12%")
    check_answer_phrase(judge, answer, "top_gainer_price", "$0.766591")
    check_answer_phrase(judge, answer, "top_gainer_mcap", "$186.98M")
    check_answer_phrase(judge, answer, "top_gainer_supply", "243,905,091")
    check_answer_phrase(judge, answer, "one_hour_mover", "Quant")
    check_answer_phrase(judge, answer, "one_hour_pct", "+2.33%")
    check_answer_phrase(judge, answer, "one_hour_price", "$266.71")
    check_answer_ordered(judge, answer, "priciest_three",
                         ["Bitcoin", "PAX Gold", "Tether Gold"])
    check_answer_phrase(judge, answer, "vol_top", "Tether")
    check_answer_phrase(judge, answer, "vol_top_24h", "+0.01%")
    check_answer_phrase(judge, answer, "vol_top_mcap", "$183.80B")
    check_answer_phrase(judge, answer, "markets_top_pair", "BTC/USDT")
    check_answer_phrase(judge, answer, "markets_top_exchange", "Binance")
    check_answer_phrase(judge, answer, "markets_top_volume", "$1.11B")
    check_answer_phrase(judge, answer, "page2_top", "Bitcoin SV")
    check_answer_number(judge, answer, "xrp_rank", 5)
    check_answer_phrase(judge, answer, "xrp_price", "$1.49")
    check_answer_phrase(judge, answer, "xrp_7d", "-5.21%")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
