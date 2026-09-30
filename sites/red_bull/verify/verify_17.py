#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--17 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
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

TASK_ID = "Red Bull--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/energydrink$",
        r"/energydrink/red-bull-coconut-edition$",
        r"/energydrink/red-bull-apple-edition$",
        r"/energydrink/red-bull-sea-blue-edition$",
        r"/energydrink/red-bull-iced-edition-sugarfree$",
        r"/energydrink/red-bull-pink-edition$",
        r"/energydrink/red-bull-sugarfree$",
        r"/energydrink/red-bull-summer-edition-sugarfree$",
    ])
    # r2 re-anchor: seven product pages, flavors attributed to the right Edition
    check_answer_regex(judge, answer, "coconut_flavor", r"Coconut[^.;]{0,12}Coconut Berry")
    check_answer_regex(judge, answer, "apple_flavor", r"Apple[^.;]{0,12}Fuji Apple")
    check_answer_regex(judge, answer, "seablue_flavor", r"Sea Blue[^.;]{0,12}Juneberry")
    check_answer_number(judge, answer, "iced_sf_caf", 80)
    check_answer_number(judge, answer, "pink_sug", 26)
    check_answer_any(judge, answer, "sugarfree_sizes", [
        "8.4 fl oz, 12 fl oz, 16 fl oz, 20 fl oz",
        "8.4 fl oz · 12 fl oz · 16 fl oz · 20 fl oz",
    ])
    check_answer_regex(judge, answer, "summer_sf_flavor", r"Summer[^.;]{0,30}Sudachi Lime")
    check_answer_number(judge, answer, "summer_sf_caf", 80)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
