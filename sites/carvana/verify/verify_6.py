#!/usr/bin/env python3
"""Deterministic verifier for Carvana--6 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "car_search",
                        ['/cars'])
    check_visited_any(judge, traj, "single_owner",
                        ['/cars\\?[^ ]*single_owner=1'])
    check_visited_any(judge, traj, "accident_free",
                        ['/cars\\?[^ ]*accident_free=1'])
    check_visited_any(judge, traj, "price_20k",
                        ['/cars\\?[^ ]*price_max=20000'])
    check_visited_any(judge, traj, "open_first",
                        ['/vehicle/4255570'])
    check_visited_any(judge, traj, "open_first_20k",
                        ['/vehicle/4443493'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "open_cheapest",
                        ['/vehicle/4661379'])
    check_visited_any(judge, traj, "sort_mileage_asc",
                        ['/cars\\?[^ ]*sort=mileage_asc'])
    check_visited_any(judge, traj, "open_lowest_mileage",
                        ['/vehicle/4452259'])
    check_answer_number(judge, answer, "single_owner_count", 20)
    check_answer_number(judge, answer, "so_af_count", 18)
    check_answer_phrase(judge, answer, "first_model", 'Kia Telluride')
    check_answer_phrase(judge, answer, "first_mileage", '65,981 miles')
    check_answer_money(judge, answer, "first_price", 26990)
    check_answer_phrase(judge, answer, "first_prior_use", 'Personal')
    check_answer_number(judge, answer, "so_af_20k_count", 7)
    check_answer_phrase(judge, answer, "first20k_model", 'Tiguan')
    check_answer_any(judge, answer, "first20k_engine", ['4-Cyl, Turbo, 2.0 Liter', '4-Cyl', '2.0 Liter', 'Turbo'])
    check_answer_phrase(judge, answer, "first20k_color", 'White')
    check_answer_phrase(judge, answer, "cheapest_model", 'smart fortwo')
    check_answer_money(judge, answer, "cheapest_price", 11990)
    check_answer_number(judge, answer, "cheapest_mpg", 124)
    check_answer_phrase(judge, answer, "cheapest_city", 'Wood Village')
    check_answer_phrase(judge, answer, "lowest_mileage_model", 'Nissan LEAF')
    check_answer_phrase(judge, answer, "lowest_mileage", '29,197 miles')
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
