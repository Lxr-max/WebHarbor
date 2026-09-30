#!/usr/bin/env python3
"""Deterministic verifier for CoinMarketCap--8 (coinmarketcap).

Ground truth below is HARDCODED (frozen from the reviewer's independent
Playwright round on the review container wh-coinmarketcap-review, container
seed sha256 f0d2d46b01bab8896f026929be4ae1ded19b8eb1ea2d969583857ac562eb427c,
md5 990af4a551228a1877ae0118ad3ae3b0) — never read from tasks.jsonl.
All values are the frozen 2026-09-29/30 UTC capture snapshot.

r2-fix note (H3 resolved): the signup email field is
``<input type="text" required>`` now, so the browser no longer intercepts
'not-an-email' and the server-side error text is reachable through honest UI
use. This verifier gates the exact server error string.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "CoinMarketCap--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_path(judge, traj, "nav_login", r"/login")
    check_visited_path(judge, traj, "nav_signup", r"/signup")
    check_answer_phrase(judge, answer, "wrong_pw_error",
                        "Your email and password does not match. Please try again.")
    check_answer_phrase(judge, answer, "invalid_email_account",
                        "The email you entered is not in the correct format. Please check.")
    check_answer_phrase(judge, answer, "short_pw_error",
                        "Your password must be at least 8 characters long.")
    check_answer_phrase(judge, answer, "duplicate_email_error",
                        "The email you entered is already registered. Please log in.")
    check_answer_regex(judge, answer, "greeting", r"Hi,\s*\w+")
    check_only_tables_changed(judge, initial, after, {"users"})
    check_rows_added(judge, initial, after, "users",
                     [(None, 'rx:.+@.+[.].+', None, None, 0, "2026-09-29")],
                     "users_added")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
