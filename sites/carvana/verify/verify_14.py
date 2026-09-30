#!/usr/bin/env python3
"""Deterministic verifier for Carvana--14 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "truck_browse",
                        ['/cars\\?[^ ]*body=Truck'])
    check_visited_any(judge, traj, "diesel_filter",
                        ['/cars\\?[^ ]*fuel=Diesel'])
    check_visited_any(judge, traj, "open_diesel",
                        ['/vehicle/4120245'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4120245/payment-estimate'])
    check_visited_any(judge, traj, "convertible_browse",
                        ['/cars\\?[^ ]*body=Convertible'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4772038'])
    check_visited_any(judge, traj, "cleared",
                        ['^https?://[^/]+/cars/?$'])
    check_visited_any(judge, traj, "sort_price_desc",
                        ['/cars\\?[^ ]*sort=price_desc'])
    check_visited_any(judge, traj, "open_priciest",
                        ['/vehicle/4631612'])
    check_answer_number(judge, answer, "truck_count", 102)
    check_answer_number(judge, answer, "diesel_count", 5)
    check_answer_phrase(judge, answer, "diesel_model", 'Ram 2500 Crew Cab')
    check_answer_money(judge, answer, "diesel_price", 61590)
    check_answer_phrase(judge, answer, "diesel_mileage", '17 miles')
    check_answer_any(judge, answer, "diesel_engine", ['Cummins High Output 6.7L I-6', 'Cummins'])
    check_answer_number(judge, answer, "est_5000_72", 1078)
    check_answer_number(judge, answer, "convertible_count", 49)
    check_answer_phrase(judge, answer, "conv_model", 'MINI Convertible')
    check_answer_money(judge, answer, "conv_price", 14590)
    check_answer_phrase(judge, answer, "conv_color", 'Red')
    check_answer_number(judge, answer, "snapshot_total", 53866)
    check_answer_absent(judge, answer, "snapshot_money_render", '$53,866')
    check_answer_phrase(judge, answer, "priciest_model", 'Porsche 911')
    check_answer_money(judge, answer, "priciest_price", 159590)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
