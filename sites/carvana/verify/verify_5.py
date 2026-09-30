#!/usr/bin/env python3
"""Deterministic verifier for Carvana--5 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "login",
                        ['/authn/login'])
    check_visited_any(judge, traj, "favorites",
                        ['/account/favorites'])
    check_visited_any(judge, traj, "modely_search",
                        ['/cars\\?[^ ]*q=Tesla\\+Model\\+Y', '/cars\\?[^ ]*make=Tesla[^ ]*model=Model\\+Y'])
    check_visited_any(judge, traj, "open_modely",
                        ['/vehicle/4650840'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4650840/payment-estimate'])
    check_visited_any(judge, traj, "open_civic",
                        ['/vehicle/4584722'])
    check_visited_any(judge, traj, "open_model3",
                        ['/vehicle/4543314'])
    check_answer_money(judge, answer, "saved_model3", 17990)
    check_answer_money(judge, answer, "saved_rav4", 31990)
    check_answer_money(judge, answer, "saved_civic", 28990)
    check_answer_phrase(judge, answer, "saved_1", 'Tesla Model 3')
    check_answer_phrase(judge, answer, "saved_2", 'Toyota RAV4')
    check_answer_phrase(judge, answer, "saved_3", 'Honda Civic')
    check_answer_number(judge, answer, "modely_count", 21)
    check_answer_money(judge, answer, "modely_price", 40590)
    check_answer_number(judge, answer, "est_2000_60_great", 837)
    check_answer_number(judge, answer, "count_after_save", 4)
    check_answer_count_at_least(judge, answer, "remaining_three", ['Model Y', 'Model 3', 'Civic'], 3)
    check_answer_money(judge, answer, "remaining_has_modely", 40590)
    check_answer_money(judge, answer, "remaining_has_model3", 17990)
    check_answer_money(judge, answer, "remaining_has_civic", 28990)
    check_answer_phrase(judge, answer, "civic_mileage", '15,642 miles')
    check_answer_phrase(judge, answer, "civic_body", 'Hatchback')
    check_answer_number(judge, answer, "civic_est", 487)
    check_answer_money(judge, answer, "model3_price", 17990)
    check_answer_phrase(judge, answer, "model3_mileage", '105,188 miles')
    check_only_tables_changed(judge, initial, after, {'favorites'})
    check_rows_added(judge, initial, after, "favorites",
                      [[None, 1, 355, '2026-09-29']], "modely_saved")
    check_rows_removed(judge, initial, after, "favorites",
                        [[None, 1, 18, None]], "rav4_removed")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
