#!/usr/bin/env python3
"""Deterministic verifier for Carvana--11 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "login",
                        ['/authn/login'])
    check_visited_any(judge, traj, "cx5_search",
                        ['/cars\\?[^ ]*q=Mazda\\+CX-5', '/cars\\?[^ ]*make=MAZDA[^ ]*model=CX-5'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4739440'])
    check_visited_any(judge, traj, "checkout",
                        ['/vehicle/4739440/checkout'])
    check_visited_any(judge, traj, "order_page",
                        ['/order/CV-200042'])
    check_visited_any(judge, traj, "orders",
                        ['/account/orders'])
    check_answer_number(judge, answer, "cx5_year", 2016)
    check_answer_phrase(judge, answer, "cx5_mileage", '84,486 miles')
    check_answer_money(judge, answer, "cx5_price", 16990)
    check_answer_phrase(judge, answer, "order_number", 'CV-200042')
    check_answer_any(judge, answer, "payment_method", ['cash', 'Cash'])
    check_answer_money(judge, answer, "trade_credit", 5000)
    check_answer_phrase(judge, answer, "delivery_date", '2026-10-06')
    check_answer_phrase(judge, answer, "cx5_color", 'White')
    check_answer_phrase(judge, answer, "cx5_fuel", 'Gas')
    check_answer_ordered(judge, answer, "timeline", ['Order placed', 'Delivery scheduled'])
    check_only_tables_changed(judge, initial, after, {'order_events', 'orders'})
    check_rows_added(judge, initial, after, "orders",
                      [[None, 'CV-200042', 3, 1013, 'cash', 0, 5000, None, None, None, '2026-10-06', '4:00 PM - 6:00 PM', 'Chicago', 'IL', '1040 N State St', '60610', 'Delivery scheduled', '2026-09-29']], "order_row_added")
    check_rows_added(judge, initial, after, "order_events",
                      [[None, 4, 'Order placed', 'Order placed online', '2026-09-29'], [None, 4, 'Delivery scheduled', 'rx:Delivery scheduled for 2026-10-06', '2026-09-29']], "order_events_added")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
