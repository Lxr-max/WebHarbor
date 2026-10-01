#!/usr/bin/env python3
"""Deterministic verifier for NYSE--13 (nyse).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the r2 review container wh-nyse-r2, seed md5
b7c3bbfa3a7a64b8d09b4e7fb3323fd9, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "NYSE--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Bell Vanguard title/date; Opening Bell Sept count + last-page top;
    # About The Bell first sentence; bob watchlist symbols + 2nd last price.
    # Read-only.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/bell/calendar\?q=Vanguard",
        r"/bell/calendar\?[^ ]*type=Opening\+Bell[^ ]*from=2026-09-01[^ ]*to=2026-09-30",
        r"/bell/calendar\?[^ ]*type=Opening\+Bell[^ ]*from=2026-09-01[^ ]*to=2026-09-30[^ ]*page=2",
        r"/bell(?!/calendar)",
        r"/login",
        r"/watchlist",
    ])
    check_answer_regex(judge, answer, "vanguard_title", r"the vanguard group[^\n]*rings the closing bell")
    check_answer_phrase(judge, answer, "vanguard_date", "September 29th, 2026")
    check_answer_number(judge, answer, "sep_opening_count", 21)
    check_answer_regex(judge, answer, "last_top_title", r"oracle[^\n]*rings the opening bell")
    check_answer_phrase(judge, answer, "bell_intro_first",
        "One of the most familiar images of the NYSE on the evening news is the loud ringing of a bell")
    check_answer_count_at_least(judge, answer, "bob_symbols", ["AAPL", "TSLA"], 2)
    check_answer_price(judge, answer, "second_last_price", 352.84)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
