#!/usr/bin/env python3
"""Deterministic verifier for Trader Joe's--4 (trader_joes).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright r2 rounds on the review container tj-review-r2-container
built over the fix commit fb73dbfa, seed md5
34e1af0cc66a317223e889081c2381b4, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Trader Joe's--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Announcements categories; newest opening; newest recall; gift cards; subscribe.
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/home/announcements\?category=store-openings",
        r"/home/announcements\?category=caring-for-our-communities",
        r"/home/announcements\?category=customer-updates",
        r"/home/announcements\?category=recalls",
        r"/home/announcements\?category=special-trading-hours",
        r"/home/gift-card-balance-inquiry",
        r"/home/subscribe",
    ])
    check_answer_number(judge, answer, "customer_updates", 3)
    check_answer_number(judge, answer, "store_openings", 52)
    check_answer_number(judge, answer, "special_trading_hours", 0)
    check_answer_number(judge, answer, "caring", 1)
    check_answer_number(judge, answer, "recalls", 2)
    check_answer_phrase(judge, answer, "newest_opening", "Herriman, UT")
    check_answer_phrase(judge, answer, "newest_opening_date", "2026-09-28")
    check_answer_phrase(judge, answer, "recall_product", "Fiesta Salad with Shrimp")
    check_answer_price(judge, answer, "gc1_balance", 25.00)
    check_answer_price(judge, answer, "gc2_balance", 12.49)
    check_answer_phrase(judge, answer, "subscribe_confirm", "Welcome aboard!")

    check_only_tables_changed(judge, initial, after, {"subscribers"})
    check_rows_added(judge, initial, after, "subscribers",
                     [[None, "news.hound@example.com", "subscribed", None]],
                     "subscribe_news_hound")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
