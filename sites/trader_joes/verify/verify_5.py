#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--5 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_regex, check_answer_zero_or_phrase, check_read_only,
    check_rows_added, check_rows_removed, check_rows_changed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Trader Joe's--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Four gift card balances; no-PIN phone; subscribe + unsubscribe; dana My Store.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/gift-card-balance-inquiry",
        r"/home/subscribe",
        r"/home/unsubscribe",
        r"/login",
    ])
    check_answer_price(judge, answer, "gc_654321", 51.37)
    check_answer_price(judge, answer, "gc_112233", 0.00)
    check_answer_price(judge, answer, "gc_987654", 100.00)
    check_answer_price(judge, answer, "gc_445566", 12.49)
    check_answer_phrase(judge, answer, "no_pin_phone", "1-888-556-6619")
    check_answer_phrase(judge, answer, "subscribe_confirm", "Welcome aboard!")
    # r2: the unsubscribe confirmation now renders (subscribe.html gained a
    # {% if removed %} block in the fix round)
    check_answer_regex(judge, answer, "unsubscribe_confirm",
                       r"unsubscribed|removed from the Trader Joe.s eNewsletter")
    check_answer_phrase(judge, answer, "dana_mystore", "Charlotte - Piper Glen (742)")
    check_only_tables_changed(judge, initial, after, {"subscribers"})
    check_rows_added(judge, initial, after, "subscribers",
                     [[None, "felice.t@example.com", "unsubscribed", None]],
                     "felice_subscribed_then_unsubscribed")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
