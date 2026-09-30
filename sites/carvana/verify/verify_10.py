#!/usr/bin/env python3
"""Deterministic verifier for Carvana--10 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "ram_search",
                        ['/cars\\?[^ ]*q=Ram\\+2500', '/cars\\?[^ ]*make=Ram'])
    check_visited_any(judge, traj, "open_2025",
                        ['/vehicle/4120245'])
    check_visited_any(judge, traj, "price_50k",
                        ['/cars\\?[^ ]*price_max=50000'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4766525'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4120245/payment-estimate'])
    check_answer_money(judge, answer, "price", 61590)
    check_answer_phrase(judge, answer, "mileage", '17 miles')
    check_answer_number(judge, answer, "est_0down", 980)
    check_answer_any(judge, answer, "engine", ['Cummins High Output 6.7L I-6', 'Cummins'])
    check_answer_phrase(judge, answer, "drivetrain", 'RWD')
    check_answer_phrase(judge, answer, "default_apr", '5.49')
    check_answer_money(judge, answer, "taxes_fees", 6644)
    check_answer_number(judge, answer, "ram_50k_count", 2)
    check_answer_number(judge, answer, "cheapest_year", 2021)
    check_answer_money(judge, answer, "cheapest_price", 43590)
    check_answer_phrase(judge, answer, "cheapest_trim", 'Tradesman')
    check_answer_phrase(judge, answer, "cheapest_mileage", '43,358 miles')
    check_answer_number(judge, answer, "monthly_84_exc", 837)
    check_answer_money(judge, answer, "financed", 58234)
    check_answer_number(judge, answer, "monthly_72_exc", 951)
    check_answer_number(judge, answer, "monthly_72_poor", 1138)
    check_answer_number(judge, answer, "monthly_15k_poor", 1040)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
