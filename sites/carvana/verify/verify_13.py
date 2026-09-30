#!/usr/bin/env python3
"""Deterministic verifier for Carvana--13 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "mustang_search",
                        ['/cars\\?[^ ]*q=Mustang', '/cars\\?[^ ]*make=Ford[^ ]*model=Mustang'])
    check_visited_any(judge, traj, "sort_year_desc",
                        ['/cars\\?[^ ]*sort=year_desc'])
    check_visited_any(judge, traj, "open_newest",
                        ['/vehicle/4315759'])
    check_visited_any(judge, traj, "sort_mileage_asc",
                        ['/cars\\?[^ ]*sort=mileage_asc'])
    check_visited_any(judge, traj, "open_lowest",
                        ['/vehicle/4715177'])
    check_visited_any(judge, traj, "year_2020",
                        ['/cars\\?[^ ]*year_min=2020'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4315759/payment-estimate'])
    check_answer_number(judge, answer, "mustang_count", 21)
    check_answer_number(judge, answer, "newest_year", 2025)
    check_answer_money(judge, answer, "newest_price", 39590)
    check_answer_phrase(judge, answer, "newest_mileage", '15,493 miles')
    check_answer_phrase(judge, answer, "newest_engine", '5L V-8 DOHC')
    check_answer_phrase(judge, answer, "newest_transmission", '10-speed automatic')
    check_answer_phrase(judge, answer, "newest_drivetrain", 'RWD')
    check_answer_phrase(judge, answer, "lowest_mileage", '4,421 miles')
    check_answer_phrase(judge, answer, "lowest_model", '2024 Ford Mustang')
    check_answer_money(judge, answer, "lowest_price", 31590)
    check_answer_phrase(judge, answer, "lowest_exterior", 'Blue')
    check_answer_phrase(judge, answer, "lowest_interior", 'Other')
    check_answer_number(judge, answer, "mustang_2020_count", 9)
    check_answer_money(judge, answer, "first_2020_price", 39590)
    check_answer_phrase(judge, answer, "gt_premium", 'GT Premium')
    check_answer_number(judge, answer, "monthly_66", 767)
    check_answer_number(judge, answer, "monthly_66_4000", 731)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
