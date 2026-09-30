#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--16 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

KNOWN-GAPS (review findings): the glossary index label states
"1334 terms captured" (and renders all 1,334 entries; only 9 have full
articles) — the count answer is read from the page label (the upstream
glossary also displays its term count), accepted as either 1334 or 1,334.
The Stablecoin article's four types (fiat-backed, commodity-backed,
crypto-backed, algorithmic) are the upstream-verbatim article text.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_glossary", r"/academy/glossary")
    check_visited_path(judge, traj, "nav_stablecoin", r"/academy/glossary/stablecoin")
    check_visited_all(judge, traj, "nav_articles",
                      [r"/academy/glossary/hodl", r"/academy/glossary/blockchain",
                       r"/academy/glossary/smart-contract", r"/academy/glossary/gas",
                       r"/academy/glossary/bear-market", r"/academy/glossary/bull-market",
                       r"/academy/glossary/defi"])
    check_answer_number(judge, answer, "terms_count", 1334)
    check_answer_phrase(judge, answer, "stablecoin_difficulty", "Easy")
    check_answer_count_at_least(judge, answer, "stablecoin_types",
                                ["fiat-backed", "commodity-backed", "crypto-backed", "algorithmic"], 4)
    check_answer_phrase(judge, answer, "hodl_difficulty", "Easy")
    check_answer_regex(judge, answer, "hodl_strategy", r"hold|never sell|conviction")
    check_answer_regex(judge, answer, "blockchain_block", r"block")
    check_answer_phrase(judge, answer, "smart_contract_difficulty", "Moderate")
    check_answer_regex(judge, answer, "gas_measures", r"computational|transaction|processing")
    check_answer_regex(judge, answer, "bear_pct", r"20%")
    check_answer_regex(judge, answer, "bull_def", r"rise|rising|uptrend|upward")
    check_answer_regex(judge, answer, "defi_movement", r"decentraliz|financial intermediar|peer")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
