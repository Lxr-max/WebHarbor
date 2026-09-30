#!/usr/bin/env python3
"""Deterministic verifier for Carvana--18 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "financing",
                        ['/financing'])
    check_visited_any(judge, traj, "hybrid_filter",
                        ['/cars\\?[^ ]*fuel=Hybrid'])
    check_visited_any(judge, traj, "open_hybrid",
                        ['/vehicle/4545578'])
    check_visited_any(judge, traj, "price_25k",
                        ['/cars\\?[^ ]*price_max=25000'])
    check_visited_any(judge, traj, "estimator",
                        ['/vehicle/4545578/payment-estimate'])
    check_answer_phrase(judge, answer, "sample_apr", '6.99')
    check_answer_number(judge, answer, "sample_term", 75)
    check_answer_any(judge, answer, "sample_down", ['$0', 'zero', '0 down'])
    check_answer_number(judge, answer, "approval_rate", 99)
    check_answer_number(judge, answer, "hybrid_count", 57)
    check_answer_phrase(judge, answer, "first_model", 'RAV4 Hybrid')
    check_answer_money(judge, answer, "first_price", 21990)
    check_answer_money(judge, answer, "taxes_fees", 2536)
    check_answer_number(judge, answer, "hybrid_25k_count", 19)
    check_answer_phrase(judge, answer, "first_25k_mileage", '101,467 miles')
    check_answer_number(judge, answer, "monthly_66_4k", 393)
    check_answer_number(judge, answer, "monthly_66_8k", 316)
    check_answer_number(judge, answer, "monthly_60_8k", 341)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
