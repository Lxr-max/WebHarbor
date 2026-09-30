#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--0 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=tent")
    check_visited_path(judge, traj, "nav_pdp", r"marmot-tungsten-tent-2-person-3-season.*color=SOLREDSUN")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_visited_path(judge, traj, "nav_checkout", r"/checkout")
    check_visited_path(judge, traj, "nav_confirm", r"/order-confirmation/9000000685")
    # title as rendered on the PDP (brand shows separately above it)
    check_answer_phrase(judge, answer, "title", 'Tungsten Tent: 2-Person 3-Season')
    check_answer_money(judge, answer, "solar_price", 209.21)
    check_answer_number(judge, answer, "reviews", 57)
    check_answer_number(judge, answer, "order_number", 9000000685)
    check_answer_money(judge, answer, "total", 418.42)
    check_answer_money(judge, answer, "subtotal", 418.42)
    check_only_tables_changed(judge, initial, after, {"orders", "order_items"})
    check_rows_added(judge, initial, after, "orders",
                      [[None, None, "weekend.camper@example.com", "9000000685", "placed", "2026-09-30", "Standard", 0, 41842, 13948, 41842, "1111", "rx:.*Casey Reyes.*Boulder.*80302.*"]], "order_row")
    check_rows_added(judge, initial, after, "order_items",
                      [[None, 5, "MARZ9NR", "Tungsten Tent: 2-Person 3-Season", "Marmot", "Solar/Red Sun", "One Size", 20921, 27895, 2]], "order_item_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
