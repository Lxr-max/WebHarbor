#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--2 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_2.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--2"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*discipline=Motocross",
        r"/events/red-bull-barn-find-open$",
        r"/events\?[^ ]*discipline=DTM",
        r"/events/dtm-nuerburgring$",
        r"/events/dtm-hockenheimring$",
        r"/events\?[^ ]*discipline=esports",
        r"/events/red-bull-wings-cup-united-states-2026$",
    ])
    check_answer_phrase(judge, answer, "iowa_venue", "Oak Ridge MX Track, Garwin, IA")
    # r2 re-anchor: event pages now render the standfirst on the Info tab, so
    # the celebrated era ("the 90's and early 2000's") is on the page and must
    # be reported; invented eras or honest-absence reports no longer pass
    check_answer_regex(judge, answer, "era", r"90[’']s and early 2000[’']?s")
    check_answer_phrase(judge, answer, "nurburgring_dates", "August 15")
    check_answer_phrase(judge, answer, "hockenheimring_dates", "October 10")
    check_answer_phrase(judge, answer, "wings_dates", "September 18")
    check_answer_phrase(judge, answer, "wings_dates_end", "December 4, 2026")
    check_answer_phrase(judge, answer, "wings_badge", "Upcoming event")
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
