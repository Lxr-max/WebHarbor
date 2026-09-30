#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--15 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
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

TASK_ID = "Red Bull--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*country=DE",
        r"/events/red-bull-stuttgart-cerro-abajo$",
        r"/events/dtm-sachsenring$",
        r"/events/dtm-oschersleben$",
        r"/events/adac-mx-masters-fuerstlich-drehna$",
        r"/events/adac-mx-masters-gaildorf$",
        r"/events/drift-masters-germany$",
    ])
    check_answer_number(judge, answer, "de_total", 9)
    check_answer_number(judge, answer, "de_upcoming", 2)
    check_answer_count_at_least(judge, answer, "finished_names", [
        "Oschersleben", "Gaildorf", "Drift Masters", "Nürburgring",
        "Stuttgart", "Sachsenring", "Fürstlich Drehna",
    ], 7)
    check_answer_phrase(judge, answer, "stuttgart_city", "Stuttgart")
    # r2 re-anchor: the event page now renders the standfirst, so what the page
    # says riders face (steep staircases, narrow streets, parks, monuments and
    # obstacles) is on the page and must be reported
    check_answer_any(judge, answer, "riders_face", [
        "steep staircases", "narrow streets, parks, monuments",
    ])
    check_answer_phrase(judge, answer, "sachsenring_dates", "September 12")
    # r2 re-anchor: the Oschersleben DTM round and both ADAC MX venues
    check_answer_phrase(judge, answer, "oschersleben_dates", "July 25")
    check_answer_phrase(judge, answer, "drehna_venue", "Fürstlich Drehna")
    check_answer_phrase(judge, answer, "gaildorf_venue", "Gaildorf")
    check_answer_phrase(judge, answer, "drift_venue", "Ferropolis")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
