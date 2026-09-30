#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--17 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

KNOWN-GAP (review finding): the task's tenth glossary article,
"51% Attack", exists in the mirror (excerpt + difficulty, reachable at
/academy/glossary/51-attack) but is NOT linked from the glossary index (only
the nine full-article terms are); the honest walk reaches it by URL
construction from the visible slug pattern. The navigation gate accepts
that URL.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_faq", r"/faq/")
    check_visited_path(judge, traj, "nav_methodology", r"/methodology/")
    check_visited_path(judge, traj, "nav_glossary", r"/academy/glossary")
    check_visited_all(judge, traj, "nav_articles",
                      [r"/academy/glossary/altcoin", r"/academy/glossary/hodl",
                       r"/academy/glossary/stablecoin", r"/academy/glossary/blockchain",
                       r"/academy/glossary/smart-contract", r"/academy/glossary/gas",
                       r"/academy/glossary/bear-market", r"/academy/glossary/bull-market",
                       r"/academy/glossary/defi", r"/academy/glossary/51-attack"])
    check_answer_phrase(judge, answer, "formula",
                        "Market Cap = Price X Circulating Supply")
    check_answer_regex(judge, answer, "supply_difference", r"circulating|available|trad")
    check_answer_regex(judge, answer, "why_circulating", r"market|represent|available")
    check_answer_regex(judge, answer, "time_zone", r"UTC")
    check_answer_regex(judge, answer, "change_base", r"24|volume|day")
    check_answer_regex(judge, answer, "buy_crypto", r"CoinMarketCap does not|not.*(buy|sell|trade)|exchange")
    check_answer_regex(judge, answer, "methodology_heading", r"methodology|method")
    check_answer_phrase(judge, answer, "altcoin_difficulty", "Easy")
    check_answer_phrase(judge, answer, "hodl_difficulty", "Easy")
    check_answer_phrase(judge, answer, "stablecoin_difficulty", "Easy")
    check_answer_phrase(judge, answer, "blockchain_difficulty", "Easy")
    check_answer_phrase(judge, answer, "smart_contract_difficulty", "Moderate")
    check_answer_phrase(judge, answer, "gas_difficulty", "Easy")
    check_answer_phrase(judge, answer, "bear_difficulty", "Easy")
    check_answer_phrase(judge, answer, "bull_difficulty", "Easy")
    check_answer_phrase(judge, answer, "defi_difficulty", "Moderate")
    check_answer_phrase(judge, answer, "attack51_difficulty", "Easy")
    check_answer_regex(judge, answer, "bear_definition", r"20%|twenty")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
