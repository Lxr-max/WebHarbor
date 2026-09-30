#!/usr/bin/env python3
"""Deterministic verifier for Carvana--7 (carvana, r2 reviewer contract).

Ground truth HARDCODED below — transcribed from the r2 reviewer's honest
Playwright walks of the rebuilt mirror (seed md5 b93c6c2e...), never read
from tasks.jsonl and never fetched live at grading time.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Carvana--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_any(judge, traj, "sell_intro",
                        ['/sell-my-car'])
    check_visited_any(judge, traj, "sell_offer",
                        ['/sell-my-car/offer'])
    check_visited_any(judge, traj, "login",
                        ['/authn/login'])
    check_visited_any(judge, traj, "orders",
                        ['/account/orders'])
    check_answer_money(judge, answer, "offer_good_45k", 18971)
    check_answer_money(judge, answer, "offer_excellent_45k", 20621)
    check_answer_money(judge, answer, "offer_good_60k", 18346)
    check_answer_regex(judge, answer, "offer_increased", 'increas|higher|up \\$?1,650|more')
    check_answer_phrase(judge, answer, "offer_code", 'TI-91013')
    check_only_tables_changed(judge, initial, after, {'trade_in_offers'})
    check_rows_added(judge, initial, after, "trade_in_offers",
                      [[None, 2, '1HGCM82633A004352', 2020, None, None, None, 45000, 'good', 18971, 'TI-91013', '2026-09-29']], "offer_claimed")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
