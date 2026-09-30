#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--1 (coinmarketcap).

Ground truth below is HARDCODED (re-frozen from the contributor's two honest
Playwright rounds on the r2-fix container wh-coinmarketcap-fix2, image seed
sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note: the home All/Coins/Tokens type tabs are LIVE UI now (real links
that preserve the active filters), so the "switch type" steps are real clicks
and the navigation gates match the tab URLs exactly.  The task was deepened
(T1 honest depth 14→19 atomic steps) with two text-required coin-page visits:
the first coin's page for its rank (XRP, rank #5) and the Coins+DeFi first
coin's page for its 24h % (Stellar, -4.06%); because the live tabs preserve
the price/mcap ranges, the Coins+DeFi step now runs after a Clear (the
reviewer's r1 URL fallback had silently dropped the ranges).
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_mcap_filter",
                       r"mcap=10000000000%7E100000000000")
    check_visited_path(judge, traj, "nav_first_coin", r"/currencies/xrp/")
    check_visited_path(judge, traj, "nav_price_1_10", r"price=1%7E10")
    check_visited_path(judge, traj, "nav_price_10_100", r"price=10%7E100")
    check_visited_path(judge, traj, "nav_type_tokens", r"type=tokens")
    check_visited_path(judge, traj, "nav_defi", r"tag=defi")
    check_visited_path(judge, traj, "nav_type_coins", r"type=coins")
    check_visited_path(judge, traj, "nav_coinside_coin", r"/currencies/stellar/")
    check_visited_path(judge, traj, "nav_cleared", r"^https?://[^/]+/?$")
    check_answer_number(judge, answer, "mcap_count", 9)
    check_answer_count_at_least(judge, answer, "mcap_top3", ["XRP", "USDC", "Solana"], 3)
    check_answer_number(judge, answer, "first_coin_rank", 5)
    check_answer_number(judge, answer, "mcap_price_count", 1)
    check_answer_phrase(judge, answer, "mcap_price_first", "XRP")
    check_answer_phrase(judge, answer, "mcap_price_first_price", "$1.49")
    check_answer_number(judge, answer, "mcap_price2_count", 2)
    check_answer_phrase(judge, answer, "first_token", "Hyperliquid")
    check_answer_any(judge, answer, "first_token_sym", ["HYPE"])
    check_answer_phrase(judge, answer, "first_token_mcap", "$21.59B")
    check_answer_number(judge, answer, "tokens_defi_count", 2)
    check_answer_phrase(judge, answer, "coins_defi_first", "Stellar")
    check_answer_any(judge, answer, "coins_defi_first_sym", ["XLM"])
    check_answer_phrase(judge, answer, "coinside_24h", "-4.06%")
    check_answer_phrase(judge, answer, "row10", "Hyperliquid")
    check_answer_phrase(judge, answer, "row10_24h", "-1.77%")
    check_answer_number(judge, answer, "row10_rank", 10)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
