#!/usr/bin/env python3
"""Deterministic verifier for Carvana--4 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "register",
                        ['/authn/register'])
    check_visited_any(judge, traj, "wrangler_keyword_search",
                        ['/cars\\?[^ ]*q=Jeep\\+Wrangler', '/cars\\?[^ ]*q=Wrangler'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4737374'])
    check_visited_any(judge, traj, "checkout",
                        ['/vehicle/4737374/checkout'])
    check_visited_any(judge, traj, "order_page",
                        ['/order/CV-200044'])
    check_answer_any(judge, answer, "own_account", ['created a new account', 'new account', 'signed up', 'registered'])
    check_answer_number(judge, answer, "wrangler_count", 21)
    check_answer_money(judge, answer, "monthly", 398)
    check_answer_phrase(judge, answer, "order_number", 'CV-200044')
    check_answer_phrase(judge, answer, "car_bought", 'Wrangler Unlimited')
    check_answer_phrase(judge, answer, "mileage", '91,951 miles')
    check_answer_money(judge, answer, "car_price", 20590)
    check_answer_phrase(judge, answer, "delivery_date", '2026-09-30')
    check_answer_phrase(judge, answer, "delivery_window", '8:00 AM - 10:00 AM')
    check_only_tables_changed(judge, initial, after, {'users', 'orders', 'order_events'})
    check_rows_added(judge, initial, after, "users",
                      [[None, 'rx:^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$', None, None, 0, '2026-09-29']], "user_row_added")
    check_rows_added(judge, initial, after, "orders",
                      [[None, 'CV-200044', 5, 986, 'finance', 2500, 0, 60, '6.24', 398, '2026-09-30', '8:00 AM - 10:00 AM', 'Scottsdale', 'AZ', '500 Sunset Blvd', '85254', 'Delivery scheduled', '2026-09-29']], "order_row_added")
    check_rows_added(judge, initial, after, "order_events",
                      [[None, 4, 'Order placed', 'Order placed online', '2026-09-29'], [None, 4, 'Delivery scheduled', 'rx:Delivery scheduled for 2026-09-30', '2026-09-29']], "order_events_added")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
