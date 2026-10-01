#!/usr/bin/env python3
"""Deterministic verifier for NYSE--15 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # dana login; Filings total; Postponed first; NYSE-exchange count+first;
    # Filed count; Recent IPOs first Priced + latest month; Backlog.
    # Read-only.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/ipo-center/filings(\?|$)",
        r"/ipo-center/filings\?[^ ]*status=Postponed",
        r"/ipo-center/filings\?[^ ]*exchange=New\+York\+Stock\+Exchange",
        r"/ipo-center/filings\?[^ ]*status=Filed",
        r"/ipo-center/recent-ipo",
        r"/ipo-center/backlog",
    ])
    check_answer_number(judge, answer, "filings_total", 9)
    check_answer_phrase(judge, answer, "postponed_first", "Bamboo Insurance")
    check_answer_number(judge, answer, "nyse_count", 2)
    check_answer_phrase(judge, answer, "nyse_first", "Ives Ultra")
    check_answer_number(judge, answer, "filed_count", 3)
    check_answer_phrase(judge, answer, "first_priced", "Accelevation")
    check_answer_regex(judge, answer, "latest_month", r"sep['’]?26")
    check_answer_any(judge, answer, "latest_month_proceeds", ["1.72B", "1,724,503,226", "1724503226", "1.72b"])
    check_answer_phrase(judge, answer, "backlog_top", "Technology")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
