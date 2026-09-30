#!/usr/bin/env python3
"""Deterministic verifier for Carvana--2 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "car_search",
                        ['/cars'])
    check_visited_any(judge, traj, "sort_price_asc",
                        ['/cars\\?[^ ]*sort=price_asc'])
    check_visited_any(judge, traj, "mileage_cap",
                        ['/cars\\?[^ ]*mileage_max=40000'])
    check_visited_any(judge, traj, "price_20k",
                        ['/cars\\?[^ ]*price_max=20000'])
    check_visited_any(judge, traj, "body_sedan",
                        ['/cars\\?[^ ]*body=Sedan'])
    check_visited_any(judge, traj, "open_sedan",
                        ['/vehicle/4466702'])
    check_visited_any(judge, traj, "body_suv",
                        ['/cars\\?[^ ]*body=SUV'])
    check_visited_any(judge, traj, "year_2020",
                        ['/cars\\?[^ ]*year_min=2020'])
    check_visited_any(judge, traj, "open_suv",
                        ['/vehicle/4591084'])
    check_answer_number(judge, answer, "total", 1544)
    check_answer_money(judge, answer, "cheap1_price", 10990)
    check_answer_phrase(judge, answer, "cheap1", 'FIAT 500X')
    check_answer_money(judge, answer, "cheap2_price", 11990)
    check_answer_phrase(judge, answer, "cheap2", 'smart fortwo')
    check_answer_money(judge, answer, "cheap3_price", 11990)
    check_answer_phrase(judge, answer, "cheap3", 'FIAT 500X')
    check_answer_number(judge, answer, "mileage_cap_count", 670)
    check_answer_number(judge, answer, "sedan_count", 34)
    check_answer_phrase(judge, answer, "sedan_model", 'Nissan Altima')
    check_answer_money(judge, answer, "sedan_price", 19590)
    check_answer_phrase(judge, answer, "sedan_mileage", '25,812 miles')
    check_answer_phrase(judge, answer, "sedan_color", 'Black')
    check_answer_phrase(judge, answer, "sedan_fuel", 'Gas')
    check_answer_number(judge, answer, "sedan_mpg", 30)
    check_answer_number(judge, answer, "suv_count", 17)
    check_answer_phrase(judge, answer, "suv_model", 'Tiguan')
    check_answer_phrase(judge, answer, "suv_city", 'Auburn')
    check_answer_number(judge, answer, "total_clear", 1544)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
