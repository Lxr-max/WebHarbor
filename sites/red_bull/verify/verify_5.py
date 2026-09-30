#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--5 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/energydrink$",
        r"/energydrink/red-bull-summer-edition$",
        r"/energydrink/red-bull-energy-drink$",
        r"/energydrink/red-bull-red-edition$",
        r"/energydrink/red-bull-amber-edition$",
        r"/energydrink/red-bull-peach-edition$",
        r"/energydrink/red-bull-zero$",
        r"/energydrink/red-bull-sugarfree$",
    ])
    check_answer_number(judge, answer, "summer_caf", 80)
    check_answer_number(judge, answer, "summer_sug", 26)
    check_answer_phrase(judge, answer, "summer_sizes", "8.4 fl oz, 12 fl oz")
    check_answer_number(judge, answer, "orig_caf", 80)
    check_answer_number(judge, answer, "orig_sug", 27)
    check_answer_count_at_least(judge, answer, "orig_sizes",
                                ["8.4 fl oz, 12 fl oz, 16 fl oz, 20 fl oz"], 1)
    check_answer_count_at_least(judge, answer, "editions_sugarfree",
                                ["Iced", "Peach", "Pink", "Sea Blue"], 3)
    check_answer_any(judge, answer, "red_twin", ["no", "not", "without"])
    check_answer_number(judge, answer, "amber_caf", 80)
    check_answer_number(judge, answer, "amber_sug", 26)
    check_answer_number(judge, answer, "peach_caf", 80)
    check_answer_number(judge, answer, "peach_sug", 26)
    check_answer_any(judge, answer, "monk_fruit_zero", ["zero=yes", "zero: yes", "zero = yes"])
    check_answer_any(judge, answer, "monk_fruit_sf", ["sugarfree=no", "sugarfree: no", "sugarfree = no"])
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
