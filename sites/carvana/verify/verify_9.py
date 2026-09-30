#!/usr/bin/env python3
"""Deterministic verifier for Carvana--9 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_answer_sequence,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Carvana--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "login",
                        ['/authn/login'])
    check_visited_any(judge, traj, "orders",
                        ['/account/orders'])
    check_visited_any(judge, traj, "open_order_car",
                        ['/vehicle/4528064'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4528064/payment-estimate'])
    check_visited_any(judge, traj, "favorites",
                        ['/account/favorites'])
    check_answer_phrase(judge, answer, "order_number", 'CV-100019')
    check_answer_phrase(judge, answer, "order_car", 'F150 SuperCrew Cab')
    check_answer_phrase(judge, answer, "order_mileage", '49,425 miles')
    check_answer_number(judge, answer, "monthly", 462)
    check_answer_number(judge, answer, "term", 72)
    check_answer_phrase(judge, answer, "apr", '6.99')
    check_answer_money(judge, answer, "down", 4000)
    check_answer_phrase(judge, answer, "delivery_date", '2026-09-12')
    check_answer_phrase(judge, answer, "delivery_window", '10:00 AM - 12:00 PM')
    check_answer_sequence(judge, answer, "timeline_order", ['Order placed', 'Financing approved', 'Delivery scheduled', 'Out for delivery', 'Delivered'])
    check_answer_count_at_least(judge, answer, "timeline_notes", ['Order placed online', 'Financing approved at 6.99% APR', 'Delivery scheduled for 2026-09-12', 'Vehicle loaded on the delivery truck', '7-Day Money-Back Guarantee'], 4)
    check_answer_phrase(judge, answer, "delivery_city", 'Scottsdale')
    check_answer_phrase(judge, answer, "trade_in_code", 'TI-90013')
    check_answer_money(judge, answer, "trade_in_amount", 27518)
    check_answer_phrase(judge, answer, "stock", '2005002901')
    check_answer_phrase(judge, answer, "vin", '1FTEW1CPXKFD28108')
    check_answer_number(judge, answer, "est_2000_60", 577)
    check_answer_phrase(judge, answer, "truck1", 'Jeep Wrangler')
    check_answer_money(judge, answer, "truck1_price", 24990)
    check_answer_phrase(judge, answer, "truck2", 'F150 SuperCrew Cab')
    check_answer_money(judge, answer, "truck2_price", 27990)
    check_answer_phrase(judge, answer, "remaining", 'F150')
    check_answer_phrase(judge, answer, "after_relogin", 'F150')
    check_only_tables_changed(judge, initial, after, {'favorites'})
    check_rows_removed(judge, initial, after, "favorites",
                        [[None, 2, 267, None]], "wrangler_removed")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
