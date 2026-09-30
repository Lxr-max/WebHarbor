#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--18 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*discipline=Dance",
        r"/events/red-bull-dance-your-style-national-final-usa$",
        r"/stories/jreamz-wins-2026-red-bull-dance-your-style-national",
        r"/events/red-bull-dance-your-style-world-final-2026-zurich$",
        r"/events/red-bull-bc-one-cypher-usa-national-final$",
        r"/events\?[^ ]*discipline=Breaking",
        r"/events/red-bull-bc-one-world-final-toronto$",
    ])
    check_answer_phrase(judge, answer, "usa_venue", "Tampa, FL")
    check_answer_phrase(judge, answer, "usa_date", "September 19, 2026")
    check_answer_phrase(judge, answer, "story_held", "Tampa")
    check_answer_any(judge, answer, "story_winner", ["JREAMZ", "jreamz"])
    check_answer_phrase(judge, answer, "story_state", "Arizona")
    check_answer_phrase(judge, answer, "world_venue", "Hallenstadion, Zürich")
    check_answer_phrase(judge, answer, "world_date", "October 24, 2026")
    check_answer_phrase(judge, answer, "bcone_venue", "Port Pavilion on Broadway Pier")
    # r2 re-anchor: the BC One World Final Toronto leg + Dance discipline count
    check_answer_phrase(judge, answer, "toronto_venue", "Toronto")
    check_answer_phrase(judge, answer, "toronto_date", "November 29, 2026")
    check_answer_any(judge, answer, "toronto_standfirst", [
        "first time ever", "redefine what can be done on the floor",
    ])
    check_answer_number(judge, answer, "dance_count", 5)
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
