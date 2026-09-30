#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--15 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

KNOWN-GAP (review finding, still open): the historical-snapshot table rows
are NOT linked to coin pages (upstream snapshot rows link), so "open the
pages of the top four coins in that snapshot" requires hopping through the
rankings table. r2-fix note: the historical 30/90-day tabs FILTER now, so
the stablecoin's "historical data at 30 and 90 days" steps show 30 and 90
rows respectively (both views still visited; no answer gate depends on the
old same-table behavior).
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_hist", r"/historical/")
    check_visited_path(judge, traj, "nav_snapshot", r"/historical/2026-09-27/")
    check_visited_path(judge, traj, "nav_upcoming", r"/upcoming/")
    check_visited_path(judge, traj, "nav_stablecoin", r"/view/stablecoin/")
    check_visited_path(judge, traj, "nav_top_stable", r"/currencies/tether/")
    check_answer_phrase(judge, answer, "snap_top", "Bitcoin")
    check_answer_phrase(judge, answer, "snap_top_mcap", "$1,696,789,523,295.26")
    check_answer_phrase(judge, answer, "snap_top_price", "$84,458.08")
    check_answer_phrase(judge, answer, "snap_eth_mcap", "$328,032,190,023.17")
    check_answer_phrase(judge, answer, "snap_usdt_mcap", "$183,778,778,565.74")
    check_answer_phrase(judge, answer, "btc_supply_snap", "20,090,315")
    check_answer_phrase(judge, answer, "btc_vol_snap", "$19,386,591,467.90")
    check_answer_phrase(judge, answer, "btc_price_now", "$83,622.87")
    check_answer_phrase(judge, answer, "eth_price_now", "$2,677.00")
    check_answer_phrase(judge, answer, "usdt_price_now", "$0.999608")
    check_answer_phrase(judge, answer, "bnb_price_now", "$757.91")
    check_answer_number(judge, answer, "upcoming_count", 9)
    check_answer_phrase(judge, answer, "stable_top", "Tether")
    check_answer_phrase(judge, answer, "stable_vol", "$74.18B")
    check_answer_phrase(judge, answer, "stable_top_pair", "BTC/USDT")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
