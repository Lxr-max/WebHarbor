#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--5 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_gl", r"/gainers-losers/")
    check_visited_all(judge, traj, "nav_opened_coins",
                      [r"/currencies/pump-fun/", r"/currencies/hedera/",
                       r"/currencies/quant/", r"/currencies/lighter/",
                       r"/currencies/midnight-network/", r"/currencies/memecore/"])
    check_visited_path(judge, traj, "nav_trending", r"/trending-cryptocurrencies/")
    check_visited_path(judge, traj, "nav_mv", r"/most-viewed-pages/")
    check_answer_phrase(judge, answer, "g1", "Pump.fun")
    check_answer_phrase(judge, answer, "g1_24h", "+19.45%")
    check_answer_phrase(judge, answer, "g1_price", "$0.00587102")
    check_answer_phrase(judge, answer, "g2", "Quant")
    check_answer_phrase(judge, answer, "g2_24h", "+15.61%")
    check_answer_phrase(judge, answer, "g3", "Midnight")
    check_answer_phrase(judge, answer, "g3_24h", "+13.34%")
    check_answer_phrase(judge, answer, "l1", "Hedera")
    check_answer_phrase(judge, answer, "l1_24h", "-15.97%")
    check_answer_phrase(judge, answer, "l2", "Lighter")
    check_answer_phrase(judge, answer, "l2_24h", "-12.58%")
    check_answer_phrase(judge, answer, "l3", "MemeCore")
    check_answer_phrase(judge, answer, "l3_24h", "-11.04%")
    check_answer_phrase(judge, answer, "top_gainer_mcap", "$2.73B")
    check_answer_phrase(judge, answer, "top_gainer_rank", "35")
    check_answer_phrase(judge, answer, "top_loser_mcap", "$4.49B")
    check_answer_phrase(judge, answer, "g2_volume", "$763.15M")
    check_answer_phrase(judge, answer, "l2_volume", "$120.79M")
    check_answer_phrase(judge, answer, "g3_price", "$0.0323851")
    check_answer_phrase(judge, answer, "l3_price", "$1.03")
    check_answer_phrase(judge, answer, "g4_price", "$165.26")
    check_answer_phrase(judge, answer, "trending_top1", "Doppler Finance")
    check_answer_any(judge, answer, "trending_top1_sym", ["XDP"])
    check_answer_phrase(judge, answer, "trending_top1_platform", "Base")
    check_answer_phrase(judge, answer, "trending_top1_24h", "+7.29%")
    check_answer_count_at_least(judge, answer, "mv_top3", ["Asentum", "Bitcoin", "Quant"], 3)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
