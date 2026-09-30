#!/usr/bin/env python3
"""Deterministic verifier for Carvana--15 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--15"


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
                        ['/vehicle/4584722'])
    check_visited_any(judge, traj, "civic_search",
                        ['/cars\\?[^ ]*q=Honda\\+Civic', '/cars\\?[^ ]*make=Honda[^ ]*model=Civic'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4584722/payment-estimate'])
    check_visited_any(judge, traj, "open_2023",
                        ['/vehicle/4736046'])
    check_visited_any(judge, traj, "favorites",
                        ['/account/favorites'])
    check_answer_phrase(judge, answer, "order_number", 'CV-100026')
    check_answer_phrase(judge, answer, "order_car", '2022 Honda Civic')
    check_answer_number(judge, answer, "monthly", 578)
    check_answer_number(judge, answer, "term", 60)
    check_answer_phrase(judge, answer, "apr", '6.24')
    check_answer_money(judge, answer, "down", 2500)
    check_answer_phrase(judge, answer, "delivery_date", '2026-10-02')
    check_answer_phrase(judge, answer, "delivery_window", '12:00 PM - 2:00 PM')
    check_answer_phrase(judge, answer, "stock", '2005090781')
    check_answer_phrase(judge, answer, "vin", '19XFL1H8XNE022765')
    check_answer_money(judge, answer, "first_price", 28990)
    check_answer_number(judge, answer, "first_est_0down", 487)
    check_answer_number(judge, answer, "est_1500_60_great", 598)
    check_answer_money(judge, answer, "est_financed", 30752)
    check_answer_number(judge, answer, "saved_count", 4)
    check_answer_count_at_least(judge, answer, "saved_models", ['2023 Honda Civic', 'Tesla Model 3', 'Toyota RAV4', '2022 Honda Civic'], 4)
    check_only_tables_changed(judge, initial, after, {'favorites'})
    check_rows_added(judge, initial, after, "favorites",
                      [[None, 1, 959, '2026-09-29']], "civic2023_saved")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
