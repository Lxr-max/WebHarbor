#!/usr/bin/env python3
"""Deterministic verifier for Steam--15 (steam).

Ground truth below is HARDCODED from the reviewer's two independent honest
Playwright rounds on the review container wh-steam-review (image
webharbor:steam-review, built independently by the reviewer from the
contribution tree baaf57f9; seed md5 b9a24e716aa09b3702ab3a0b38d8c4de /
sha256 e6d0805e..., reproduced byte-identically; every hardcoded fact
cross-checked against the frozen seed database) — never read from
tasks.jsonl.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_money, check_answer_number, check_answer_number_absent,
    check_answer_ordered, check_answer_phrase, check_answer_regex,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Steam--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search_dc", r"/search/\\?[^ ]*term=Dead")
    check_visited_path(judge, traj, "nav_dc", r"/app/588650")
    check_visited_path(judge, traj, "nav_dlc", r"/app/1204130")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_bundle1", r"/bundle/30317")
    check_visited_path(judge, traj, "nav_bundle2", r"/bundle/46406")
    check_answer_number(judge, answer, "dlc_count", 4)
    check_answer_phrase(judge, answer, "first_dlc_name", "Dead Cells: The Bad Seed")
    check_answer_money(judge, answer, "first_dlc_price", 4.99)
    check_answer_phrase(judge, answer, "dlc_release", "Feb 11, 2020")
    check_answer_money(judge, answer, "dlc_subtotal", 4.99)
    check_answer_money(judge, answer, "dc_price", 24.99)
    check_answer_any(judge, answer, "dc_discount", ["no discount", "not on sale", "without a discount"])
    check_answer_phrase(judge, answer, "first_bundle_name", "Dead Cells: Medley of Pain Bundle")
    check_answer_money(judge, answer, "first_bundle_price", 39.95)
    check_answer_number(judge, answer, "first_bundle_items", 5)
    check_answer_money(judge, answer, "bundle_subtotal", 39.95)
    check_answer_money(judge, answer, "qty3_subtotal", 74.97)
    check_answer_phrase(judge, answer, "second_bundle_name", "Windblown + Dead Cells")
    check_answer_money(judge, answer, "second_bundle_price", 44.98)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
