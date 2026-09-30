#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--19 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note (B2 resolved): the historical-data days tabs FILTER now (the
route applies the days window), so the 90-day view shows the 90 most recent
daily rows. The task wording was adjusted to match ("the earliest date shown
in the 90-day view" = 2026-07-02, Dogecoin's 90-day view page 2); the other
walked truths (most-recent row, 365-day page-2/3 first rows, ETH 365-row
count label, SOL most-recent close) are unchanged by the fix.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_btc_hist", r"/currencies/bitcoin/historical-data/")
    check_answer_phrase(judge, answer, "recent_date", "2026-09-29")
    check_answer_phrase(judge, answer, "recent_open", "$83,500.32")
    check_answer_phrase(judge, answer, "recent_high", "$84,511.28")
    check_answer_phrase(judge, answer, "recent_low", "$82,739.10")
    check_answer_phrase(judge, answer, "recent_close", "$83,622.43")
    check_answer_phrase(judge, answer, "recent_volume", "$28.03B")
    check_visited_path(judge, traj, "nav_days90", r"days=90")
    check_visited_path(judge, traj, "nav_days365", r"days=365")
    check_answer_phrase(judge, answer, "p2_first_date", "2026-08-10")
    check_answer_phrase(judge, answer, "p3_first_date", "2026-06-21")
    check_visited_path(judge, traj, "nav_eth_hist", r"/currencies/ethereum/historical-data/")
    check_answer_number(judge, answer, "eth_rows", 365)
    check_visited_path(judge, traj, "nav_doge_hist", r"/currencies/dogecoin/historical-data/")
    check_answer_phrase(judge, answer, "doge_earliest", "2026-07-02")
    check_visited_path(judge, traj, "nav_sol_hist", r"/currencies/solana/historical-data/")
    check_answer_phrase(judge, answer, "sol_close", "$119.06")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
