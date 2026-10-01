#!/usr/bin/env python3
"""Deterministic verifier for NYSE--6 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_price, check_answer_regex,
    check_answer_zero_or_phrase, check_read_only, check_rows_added,
    check_rows_removed, check_only_tables_changed, check_screenshots,
    check_seed_contract, check_trajectory_identity, check_visited_all,
    check_visited_any, check_visited_path, final_answer, run_verifier,
)

TASK_ID = "NYSE--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # alice login; Recent IPOs (first Priced, 90d top, 180d rows);
    # Pricing Stats sector; Filings filters; Backlog. Read-only.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/ipo-center/recent-ipo(\?window=90)?",
        r"/ipo-center/recent-ipo\?window=90",
        r"/ipo-center/recent-ipo\?window=180",
        r"/ipo-center/ipo-pricing-stats",
        r"/ipo-center/filings\?[^ ]*status=Filed",
        r"/ipo-center/filings\?[^ ]*exchange=NASDAQ",
        r"/ipo-center/backlog",
    ])
    check_answer_phrase(judge, answer, "first_priced_issuer", "Accelevation")
    check_answer_price(judge, answer, "first_priced_price", 18.00)
    check_answer_phrase(judge, answer, "largest90_top", "Csquare")
    check_answer_any(judge, answer, "largest90_proceeds", ["1.21B", "1,207,479,000", "1207479000", "1.21b"])
    check_answer_number(judge, answer, "rows_180", 10)
    check_answer_phrase(judge, answer, "stats_top_sector", "Healthcare")
    check_answer_regex(judge, answer, "stats_within_pct", r"84\s*%")
    check_answer_phrase(judge, answer, "ivai_exchange", "New York Stock Exchange")
    check_answer_number(judge, answer, "nasdaq_count", 5)
    check_answer_phrase(judge, answer, "backlog_top", "Technology")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
