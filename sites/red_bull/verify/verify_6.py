#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--6 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/athletes\?[^ ]*country=United\+Kingdom",
        r"/athletes/gee-atherton$",
        r"/athletes/rachel-atherton$",
        r"/athletes/sky-brown$",
        r"/athletes/zoe-backstedt$",
        r"/athletes\?[^ ]*letter=T",
        r"/athletes/terry-adams$",
    ])
    check_answer_number(judge, answer, "uk_count", 4)
    check_answer_count_at_least(judge, answer, "uk_names",
                                ["Gee Atherton", "Rachel Atherton", "Sky Brown", "Zoe Backstedt"], 4)
    check_answer_count_at_least(judge, answer, "uk_disciplines",
                                ["Mountainbike Downhill", "Road Cycling",
                                 "Surfing Competition / Skateboard Park"], 3)
    check_answer_number(judge, answer, "career_gee", 2001)
    check_answer_number(judge, answer, "career_rachel", 2007)
    check_answer_number(judge, answer, "career_sky", 2018)
    # r2 re-anchor: the task now names the FIRST-name letter (T), which
    # surfaces Terry Adams; his profile must be opened and his discipline,
    # nationality and date of birth reported
    check_answer_any(judge, answer, "letter_t_outcome", ["terry adams", "yes"])
    # the task names the FIRST-name letter (T); a claimed letter-A lookup is a
    # knowledge-shortcut tell (the A grid does not surface Terry Adams)
    check_answer_absent(judge, answer, "letter_a_claim", "letter a")
    check_answer_phrase(judge, answer, "terry_discipline", "BMX Flatland")
    check_answer_phrase(judge, answer, "terry_nationality", "United States")
    check_answer_phrase(judge, answer, "terry_dob", "August 9, 1983")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
