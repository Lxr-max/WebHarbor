#!/usr/bin/env python3
"""Deterministic verifier for Carvana--3 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "camry_search",
                        ['/cars\\?[^ ]*make=Toyota[^ ]*model=Camry', '/cars\\?[^ ]*q=Toyota\\+Camry', '/cars\\?[^ ]*q=Camry'])
    check_visited_any(judge, traj, "sort_year_desc",
                        ['/cars\\?[^ ]*sort=year_desc'])
    check_visited_any(judge, traj, "open_newest",
                        ['/vehicle/4754196'])
    check_visited_any(judge, traj, "price_30k",
                        ['/cars\\?[^ ]*price_max=30000'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4683198'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4754196/payment-estimate'])
    check_answer_number(judge, answer, "camry_count", 20)
    check_answer_number(judge, answer, "newest_year", 2026)
    check_answer_money(judge, answer, "newest_price", 30990)
    check_answer_phrase(judge, answer, "newest_mileage", '15,201 miles')
    check_answer_phrase(judge, answer, "newest_color", 'Blue')
    check_answer_phrase(judge, answer, "newest_fuel", 'Hybrid')
    check_answer_number(judge, answer, "camry_30k_count", 15)
    check_answer_money(judge, answer, "cheapest_price", 14990)
    check_answer_phrase(judge, answer, "cheapest_year_model", '2013 Toyota Camry')
    check_answer_phrase(judge, answer, "cheapest_mileage", '109,839 miles')
    check_answer_number(judge, answer, "monthly_72", 536)
    check_answer_money(judge, answer, "financed_72", 31460)
    check_answer_number(judge, answer, "monthly_60", 623)
    check_answer_number(judge, answer, "monthly_60_excellent", 601)
    check_answer_money(judge, answer, "taxes_fees", 3470)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
