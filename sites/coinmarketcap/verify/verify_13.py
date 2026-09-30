#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--13 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

No known gaps: the task walks clean on the review container.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_memes", r"/view/memes/")
    check_visited_path(judge, traj, "nav_doge", r"/currencies/dogecoin/")
    check_visited_path(judge, traj, "nav_oracles", r"/view/oracles/")
    check_visited_path(judge, traj, "nav_lending", r"/view/lending-borowing/")
    check_visited_path(judge, traj, "nav_storage", r"/view/storage/")
    check_visited_path(judge, traj, "nav_ai", r"/view/ai-big-data/")
    check_visited_path(judge, traj, "nav_privacy", r"/view/privacy/")
    check_answer_phrase(judge, answer, "memes_mcap", "$30.58B")
    check_answer_phrase(judge, answer, "memes_7d", "-0.93%")
    check_answer_number(judge, answer, "memes_shown", 9)
    check_answer_any(judge, answer, "memes_upstream", ["5,363", "5363"])
    check_answer_phrase(judge, answer, "top_meme_24h", "+0.01%")
    check_answer_phrase(judge, answer, "doge_watchers", "2,267,570")
    check_answer_phrase(judge, answer, "doge_rank", "11")
    check_answer_any(judge, answer, "oracles_upstream", ["62", "63"])
    check_answer_phrase(judge, answer, "top_oracle", "Chainlink")
    check_answer_any(judge, answer, "lending_upstream", ["89", "90"])
    check_answer_phrase(judge, answer, "lending_top", "Aave")
    check_answer_phrase(judge, answer, "lending_top_price", "$165.26")
    check_answer_phrase(judge, answer, "storage_top", "Filecoin")
    check_answer_phrase(judge, answer, "ai_top", "NEAR Protocol")
    check_answer_phrase(judge, answer, "privacy_top", "Zcash")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
