#!/usr/bin/env python3
"""Deterministic verifier for Carvana--12 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "login",
                        ['/authn/login'])
    check_visited_any(judge, traj, "profile",
                        ['/account/profile'])
    check_visited_any(judge, traj, "favorites",
                        ['/account/favorites'])
    check_visited_any(judge, traj, "orders",
                        ['/account/orders'])
    check_answer_phrase(judge, answer, "phone_before", '(617) 555-0163')
    check_answer_phrase(judge, answer, "street_before", '77 Beacon St')
    check_answer_phrase(judge, answer, "city_before", 'Boston')
    check_answer_phrase(judge, answer, "phone_after", '(617) 555-0700')
    check_answer_phrase(judge, answer, "zip_after", '02110')
    check_answer_phrase(judge, answer, "saved_1", 'Camry Hybrid')
    check_answer_money(judge, answer, "saved_1_price", 21990)
    check_answer_phrase(judge, answer, "saved_2", 'Model Y')
    check_answer_money(judge, answer, "saved_2_price", 40590)
    check_answer_phrase(judge, answer, "remaining", 'Model Y')
    check_answer_phrase(judge, answer, "order_number", 'CV-100033')
    check_answer_phrase(judge, answer, "order_car", 'Model Y')
    check_answer_any(judge, answer, "order_status", ['Financing review', 'financing-review'])
    check_answer_phrase(judge, answer, "delivery_date", '2026-10-05')
    check_answer_phrase(judge, answer, "delivery_window", '8:00 AM - 10:00 AM')
    check_answer_sequence(judge, answer, "timeline2", ['Order placed', 'Financing review'])
    check_answer_count_at_least(judge, answer, "timeline_notes2", ['Order placed online', 'Cash purchase verification in progress'], 2)
    check_answer_phrase(judge, answer, "phone_after_relogin", '(617) 555-0700')
    check_only_tables_changed(judge, initial, after, {'favorites', 'profiles'})
    check_rows_changed(judge, initial, after, "profiles",
                        [[4, 4, '(617) 555-0700', None, None, None, '02110', None]], "profile_updated")
    check_rows_removed(judge, initial, after, "favorites",
                        [[None, 4, 774, None]], "camry_hybrid_removed")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
