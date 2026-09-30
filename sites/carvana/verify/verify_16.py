#!/usr/bin/env python3
"""Deterministic verifier for Carvana--16 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "help_hub",
                        ['/faq'])
    check_visited_any(judge, traj, "reschedule",
                        ['/help/pickup-and-delivery/can-i-reschedule-my-appointment'])
    check_visited_any(judge, traj, "token",
                        ['/help/pickup-and-delivery/can-i-keep-my-car-vending-machine-token'])
    check_visited_any(judge, traj, "autopay",
                        ['/help/payment-and-financing/can-i-add-auto-pay-after-receiving-my-car'])
    check_visited_any(judge, traj, "gap",
                        ['/help/extended-coverage-and-repairs/does-carvana-offer-gap-coverage'])
    check_visited_any(judge, traj, "tax_savings",
                        ['/help/sell-or-trade/are-there-tax-savings-to-trading-in-my-car'])
    check_visited_any(judge, traj, "business_owner",
                        ['/help/purchasing-a-car/business-owner-which-documents-can-i-provide-for-proof-of-income'])
    check_visited_any(judge, traj, "vending_buy",
                        ['/help/pickup-and-delivery/can-i-buy-a-car-i-see-inside-the-carvana-vending-machine'])
    check_visited_any(judge, traj, "certified",
                        ['/help/carvana-inventory/are-carvanas-vehicles-certified'])
    check_answer_count_at_least(judge, answer, "categories", ['About Our Vehicles', 'Payment and Financing', 'Pickup & Delivery', 'Purchasing a Car', 'Trading In & Selling', 'Vehicle Protection & Repairs'], 6)
    check_answer_count_at_least(judge, answer, "category_counts", ['1', '3', '3', '3', '3', '3'], 6)
    check_answer_phrase(judge, answer, "reschedule_answer", 'Order Placed Dashboard')
    check_answer_phrase(judge, answer, "token_answer", 'keepsake')
    check_answer_phrase(judge, answer, "autopay_answer", 'Bridgecrest')
    check_answer_number(judge, answer, "autopay_phone", 18009678526)
    check_answer_count_at_least(judge, answer, "gap_answer", ['GAP Coverage', 'Indiana', 'New York', 'Washington DC'], 3)
    check_answer_phrase(judge, answer, "tax_answer", 'tax on the difference')
    check_answer_phrase(judge, answer, "business_owner_title", 'I am a business owner. Which documents can I provide for proof of income?')
    check_answer_count_at_least(judge, answer, "vending_buy_answer", ['already sold', 'similar vehicle', 'Vending Machine'], 2)
    check_answer_count_at_least(judge, answer, "certified_answer", ['inspected and reconditioned', 'CARFAX', 'AutoCheck'], 2)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
