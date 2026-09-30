#!/usr/bin/env python3
"""Deterministic verifier for Carvana--1 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "electric_serp",
                        ['/cars\\?[^ ]*fuel=Electric'])
    check_visited_any(judge, traj, "price_30k",
                        ['/cars\\?[^ ]*price_max=30000'])
    check_visited_any(judge, traj, "open_first_ev",
                        ['/vehicle/4324860'])
    check_visited_any(judge, traj, "year_2022",
                        ['/cars\\?[^ ]*year_min=2022'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest_2022ev",
                        ['/vehicle/4452259'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4452259/payment-estimate'])
    check_visited_any(judge, traj, "sort_year_desc",
                        ['/cars\\?[^ ]*sort=year_desc'])
    check_answer_number(judge, answer, "ev_count", 108)
    check_answer_number(judge, answer, "ev_30k_count", 74)
    check_answer_phrase(judge, answer, "first_year_model", '2017 Tesla Model X')
    check_answer_phrase(judge, answer, "first_mileage", '100,361 miles')
    check_answer_money(judge, answer, "first_price", 27590)
    check_answer_phrase(judge, answer, "first_drivetrain", 'AWD')
    check_answer_number(judge, answer, "ev_30k_2022_count", 42)
    check_answer_phrase(judge, answer, "cheapest_make", 'Nissan')
    check_answer_money(judge, answer, "cheapest_price", 15990)
    check_answer_phrase(judge, answer, "cheapest_city", 'Tooele')
    check_answer_number(judge, answer, "est_monthly_2500_60_great", 300)
    check_answer_money(judge, answer, "est_financed", 15403)
    check_answer_number(judge, answer, "newest_year", 2025)
    check_answer_phrase(judge, answer, "newest_make", 'Nissan')
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
