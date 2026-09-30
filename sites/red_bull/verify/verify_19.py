#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--19 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/athletes\?[^ ]*discipline=Supercross",
        r"/athletes/eli-tomac$",
        r"/athletes\?[^ ]*discipline=BMX\+Flatland",
        r"/athletes/terry-adams$",
        r"/stories\?[^ ]*discipline=Supercross",
        r"/stories/supercross-vs-motocross$",
        r"/stories\?[^ ]*discipline=Skateboarding",
    ])
    check_answer_phrase(judge, answer, "tomac_nat", "United States")
    check_answer_phrase(judge, answer, "tomac_dob", "November 14, 1992")
    check_answer_phrase(judge, answer, "tomac_grew", "Cortez")
    check_answer_phrase(judge, answer, "terry_birthplace", "Hammond, Louisiana, USA")
    check_answer_any(judge, answer, "sx_vs_mx_diff", [
        "outdoors", "natural terrain", "long straightaways", "technical",
    ])
    check_answer_number(judge, answer, "skate_count", 1)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
