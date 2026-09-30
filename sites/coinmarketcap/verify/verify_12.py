#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--12 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note (B3 depth): the task was deepened (T12 honest depth 12→16 atomic
steps) by extending the fee comparison from five to seven text-required
exchange pages (Bybit and Gate added, each with real fee/visit questions).
The "24h volume" answers are the spot 24h volumes the exchange pages show
under "Spot Volume (24h)".
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_exchanges",
                      [r"/exchanges/binance/", r"/exchanges/coinbase-exchange/",
                       r"/exchanges/kraken/", r"/exchanges/kucoin/", r"/exchanges/bitget/",
                       r"/exchanges/bybit/", r"/exchanges/gate/"])
    check_answer_phrase(judge, answer, "binance_fees", "0.02% / 0.04%")
    check_answer_phrase(judge, answer, "coinbase_fees", "0.00% / 0.00%")
    check_answer_phrase(judge, answer, "kraken_fees", "0.02% / 0.05%")
    check_answer_phrase(judge, answer, "kucoin_fees", "0.02% / 0.06%")
    check_answer_phrase(judge, answer, "bitget_fees", "0.02% / 0.06%")
    check_answer_phrase(judge, answer, "bybit_fees", "0.02% / 0.06%")
    check_answer_phrase(judge, answer, "gate_fees", "0.01% / 0.05%")
    check_answer_phrase(judge, answer, "binance_volume", "$11.14B")
    check_answer_phrase(judge, answer, "binance_visits", "7,369,881")
    check_answer_number(judge, answer, "coinbase_visits", 4189694)
    check_answer_number(judge, answer, "kraken_visits", 1086112)
    check_answer_number(judge, answer, "kucoin_visits", 3993806)
    check_answer_number(judge, answer, "bitget_visits", 2053729)
    check_answer_number(judge, answer, "bybit_visits", 2464711)
    check_answer_number(judge, answer, "gate_visits", 2565584)
    check_answer_any(judge, answer, "lowest_taker_exchange", ["Coinbase"])
    check_answer_phrase(judge, answer, "lowest_taker_fee", "0.00%")
    check_answer_any(judge, answer, "highest_visits_exchange", ["Binance"])
    check_answer_phrase(judge, answer, "largest_volume_share", "6.46%")
    check_answer_phrase(judge, answer, "oldest_launch", "Jul 28, 2011")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
