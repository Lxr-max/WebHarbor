#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--4.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_any,
    check_answer_ordered, check_answer_phrase, check_answer_price,
    check_answer_range, check_answer_regex, check_answer_zero_or_phrase,
    check_read_only, check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_trajectory_identity, check_visited_all, check_visited_any,
    check_visited_path, final_answer, run_verifier,
)

TASK_ID = "Stanford University--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Economics BA (dept Economics, 80 units, description) -> dept page (ECON)
    # -> Economics MA (45) -> CS Minor (26) -> kind=PhD filter (41 PhD Minors,
    # first "Aeronautics & Astro (PMn)").
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/programs\?q=Economics",
        r"/programs/ECON-BA",
        r"/departments/ECONOMICS",
        r"/programs/ECON-MA",
        r"/programs\?q=Computer",
        r"/programs/CS-MIN",
        r"kind=PhD",
    ])
    check_answer_phrase(judge, answer, "econ_ba_dept", "Economics")
    check_answer_number(judge, answer, "econ_ba_min_units", 80)
    check_answer_phrase(judge, answer, "econ_ba_first_sentence",
                        "Develop a foundational understanding of the economic aspects")
    check_answer_phrase(judge, answer, "econ_subject_code", "ECON")
    check_answer_number(judge, answer, "econ_ma_min_units", 45)
    check_answer_number(judge, answer, "cs_minor_min_units", 26)
    check_answer_number(judge, answer, "phd_minor_count", 41)
    check_answer_phrase(judge, answer, "phd_minor_first_name", "Aeronautics & Astro (PMn)")
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
