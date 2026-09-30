#!/usr/bin/env python3
"""Deterministic verifier for Carvana--8 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "telluride_search",
                        ['/cars\\?[^ ]*make=Kia[^ ]*model=Telluride', '/cars\\?[^ ]*q=Kia\\+Telluride', '/cars\\?[^ ]*q=Telluride'])
    check_visited_any(judge, traj, "open_2022",
                        ['/vehicle/4255570'])
    check_visited_any(judge, traj, "open_similar",
                        ['/vehicle/4612911'])
    check_visited_any(judge, traj, "open_second",
                        ['/vehicle/4517752'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4255570/payment-estimate'])
    check_answer_number(judge, answer, "telluride_count", 21)
    check_answer_money(judge, answer, "price", 26990)
    check_answer_phrase(judge, answer, "mileage", '65,981 miles')
    check_answer_phrase(judge, answer, "engine", 'LAMBDA II 3.8L V-6 DOHC')
    check_answer_phrase(judge, answer, "transmission", '8-speed automatic')
    check_answer_phrase(judge, answer, "drivetrain", 'AWD')
    check_answer_number(judge, answer, "seating", 7)
    check_answer_phrase(judge, answer, "vin", '5XYP6DHC3NG255505')
    check_answer_phrase(judge, answer, "location", 'Rocklin')
    check_answer_number(judge, answer, "owner_review_count", 20)
    check_answer_number(judge, answer, "reviews_shown", 4)
    check_answer_any(judge, answer, "first_review_author", ['Brianne B.'])
    check_answer_number(judge, answer, "first_review_rating", 5)
    check_answer_any(judge, answer, "accidents", ['None reported', 'no accidents', 'accident-free', 'accident free'])
    check_answer_phrase(judge, answer, "prior_use", 'Personal')
    check_answer_phrase(judge, answer, "similar_model", 'FIAT 500X')
    check_answer_money(judge, answer, "similar_price", 10990)
    check_answer_phrase(judge, answer, "similar_mileage", '85,806 miles')
    check_answer_number(judge, answer, "second_price", 20590)
    check_answer_phrase(judge, answer, "second_mileage", '101,850 miles')
    check_answer_money(judge, answer, "cheapest_telluride_price", 18990)
    check_answer_number(judge, answer, "monthly_60_great", 487)
    check_answer_number(judge, answer, "monthly_72_great", 418)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
