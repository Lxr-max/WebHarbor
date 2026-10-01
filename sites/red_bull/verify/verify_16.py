#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--16 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events\?[^ ]*country=US[^ ]*status=upcoming",
        r"/events\?[^ ]*discipline=esports",
        r"/events/red-bull-wings-cup-united-states-2026$",
        r"/events/red-bull-wings-cup-united-states-2026/faqs",
        r"/events/red-bull-foam-wreckers-narragansett$",
        r"/events/red-bull-rapid-release$",
    ])
    check_answer_number(judge, answer, "us_count", 18)
    check_answer_phrase(judge, answer, "first_shown", "Virginia Beach")
    # r2 re-anchor: the Info tab renders the standfirst and the FAQs tab carries
    # the upstream GENERAL block — both must be reported from the page
    check_answer_any(judge, answer, "wings_standfirst", [
        "Play EA SPORTS FC", "Qualifiers start Sept 28, 2026",
    ])
    check_answer_any(judge, answer, "wings_fee", [
        "no entry fee", "There is no entry fee to participate in Red Bull Wings Cup",
    ])
    check_answer_phrase(judge, answer, "narr_badge", "Upcoming event")
    check_answer_absent(judge, answer, "narr_badge_negative", "Registrations open")
    check_answer_phrase(judge, answer, "narr_venue", "Narragansett Town Beach")
    check_answer_phrase(judge, answer, "rr_venue", "Walk-On's Sports Bistreaux - Burbank Restaurant")
    check_answer_any(judge, answer, "rr_fee", ["free", "Free"])
    check_read_only(judge, initial, after)



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
