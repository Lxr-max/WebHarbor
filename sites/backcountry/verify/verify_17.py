#!/usr/bin/env python3
"""Deterministic verifier for Backcountry--17 (backcountry).

Ground truth below is HARDCODED (frozen from the two independent honest-step
rounds on the dev container wh-backcountry-dev, image
webharbor:backcountry-dev, seed md5 44da2a3fc213b3ac5e76ba11453baee2 — both
rounds measured identical step counts and identical answers) — never read
from tasks.jsonl.

Audit-round correction (wh-backcountry-audit, 2026-09-30): the subcategory
color pages (/cat/<sub>/color/<c>) previously rendered UNFILTERED (the color
path segment was never applied for subcategory listings), which made this
task impossible to complete honestly — the review rounds had worked around
it with direct-URL navigations. app.py now injects the path color into the
listing args for subcategory pages, so the honest visible-element path
(filter black, then sort by Highest Price) reaches
/cat/womens-baselayers?color=black&sort=-price with the grid correctly
filtered. The nav_black_sorted gate pattern was widened from
`\?sort=-price` to `.*sort=-price` to accept the honest filter→sort order
(both filter→sort and sort→filter orders remain accepted).
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Backcountry--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_cat", r"/cat/ski")
    check_visited_path(judge, traj, "nav_sorted", r"/cat/ski\?sort=price")
    check_visited_path(judge, traj, "nav_pdp_cheap", r"smartwool-merino-250-baselayer-crew-womens")
    check_visited_path(judge, traj, "nav_breadcrumb", r"/cat/womens-baselayers")
    check_visited_all(judge, traj, "nav_black_sorted",
                       [r"/cat/womens-baselayers/color/black",
                        r"/cat/womens-baselayers.*sort=-price"])
    check_visited_path(judge, traj, "nav_pdp_first", r"patagonia-capilene-thermal-weight-bottom-womens")
    check_visited_path(judge, traj, "nav_pdp_second", r"smartwool-merino-250-baselayer-crew-womens")
    check_visited_path(judge, traj, "nav_cart", r"/cart")
    check_answer_phrase(judge, answer, "cheapest", "Classic Thermal Merino Crew Baselayer - Women's")
    check_answer_money(judge, answer, "price", 57.5)
    check_answer_phrase(judge, answer, "crumb_name", "Women's Baselayers")
    check_answer_number(judge, answer, "crumb_upstream", 230)
    check_answer_phrase(judge, answer, "first_black", "Capilene Thermal Weight Bottom - Women's")
    check_answer_money(judge, answer, "first_black_price", 109.0)
    check_answer_money(judge, answer, "subtotal", 218.0)
    check_only_tables_changed(judge, initial, after, {"cart_items"})
    check_rows_added(judge, initial, after, "cart_items",
                      [[None, None, "rx:^[0-9a-f]{32}$", "PATZBDL-CANGRE-XS", 2, "2026-09-30"]], "capilene_cart_row")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
