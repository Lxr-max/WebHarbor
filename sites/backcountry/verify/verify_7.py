#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--7 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search_boots", r"/search\?q=ski%20boots|/search\?q=ski\+boots")
    check_visited_path(judge, traj, "nav_pdp_boot", r"rossignol-alltrack-80-w-ski-boots")
    check_visited_path(judge, traj, "nav_search_rope", r"/search\?q=climbing%20rope|/search\?q=climbing\+rope")
    check_visited_path(judge, traj, "nav_pdp_rope", r"beal-zenith-climbing-rope-9\.5mm")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_phrase(judge, answer, "boot", "Alltrack 80 W Ski Boot - Women's")
    check_answer_money(judge, answer, "boot_price", 124.63)
    # boot has zero reviews: the PDP renders "No reviews yet"; accept the
    # numeric token 0 or an explicit no-reviews phrasing
    import re as _re
    from verify_lib import _norm as _n
    if _re.search(r"(?<![\d.])0(?![\d.])", answer) or "no reviews" in _n(answer):
        judge.ok("boot_reviews", "0 / no reviews")
    else:
        judge.fail("boot_reviews", "answer must state 0 reviews or no reviews")
    check_answer_phrase(judge, answer, "rope", 'Zenith Climbing Rope - 9.5mm')
    check_answer_money(judge, answer, "rope_price", 207.44)
    check_answer_money(judge, answer, "subtotal", 332.07)
    check_answer_money(judge, answer, "final_subtotal", 414.88)
    # deepened: open the rope product page from the cart line and report
    # how many colors it comes in (two: Blue, Pink)
    check_visited_path(judge, traj, "nav_rope_pdp", r"beal-zenith-climbing-rope-9\.5mm")
    check_answer_number(judge, answer, "rope_colors", 2)
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, None, "rx:^[0-9a-f]{32}$", "BEA000U-BL-S70M", 2, "2026-09-30"]], "rope_cart_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
