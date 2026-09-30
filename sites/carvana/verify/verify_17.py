#!/usr/bin/env python3
"""Deterministic verifier for Carvana--17 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "how_it_works",
                        ['/how-it-works'])
    check_visited_any(judge, traj, "certified",
                        ['/certified-program'])
    check_visited_any(judge, traj, "car_search",
                        ['/cars'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4612911'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4612911/payment-estimate'])
    check_visited_any(judge, traj, "sort_price_desc",
                        ['/cars\\?[^ ]*sort=price_desc'])
    check_visited_any(judge, traj, "open_priciest",
                        ['/vehicle/4631612'])
    check_visited_any(judge, traj, "suv_20k",
                        ['/cars\\?[^ ]*body=SUV[^ ]*price_max=20000', '/cars\\?[^ ]*price_max=20000[^ ]*body=SUV'])
    check_visited_any(judge, traj, "open_suv",
                        ['/vehicle/4318932'])
    check_answer_phrase(judge, answer, "hiw_headline", 'The New Way to Buy a Car')
    check_answer_number(judge, answer, "worry_free_days", 100)
    check_answer_phrase(judge, answer, "worry_free_miles", '4,189')
    check_answer_any(judge, answer, "seven_day", ['7-Day', '7 day', 'seven-day'])
    check_answer_any(judge, answer, "payment_options", ['PAY YOUR WAY', 'finance', 'cash'])
    check_answer_any(judge, answer, "inspection_claim", ['inspected and reconditioned'])
    check_answer_phrase(judge, answer, "certified_inspection", '150-point')
    check_answer_money(judge, answer, "cheap1", 10990)
    check_answer_money(judge, answer, "cheap2", 11990)
    check_answer_money(judge, answer, "cheap3", 11990)
    check_answer_count_at_least(judge, answer, "three_cheapest", ['FIAT 500X', 'smart fortwo', 'FIAT 500X'], 3)
    check_answer_number(judge, answer, "cheapest_est", 211)
    check_answer_phrase(judge, answer, "cheapest_city", 'Tolleson')
    check_answer_number(judge, answer, "est_3000_60", 186)
    check_answer_phrase(judge, answer, "priciest", 'Porsche 911')
    check_answer_phrase(judge, answer, "priciest_body", 'Convertible')
    check_answer_number(judge, answer, "suv_20k_count", 211)
    check_answer_phrase(judge, answer, "first_suv", 'INFINITI QX60')
    check_answer_phrase(judge, answer, "first_suv_city", 'Rocklin')
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
