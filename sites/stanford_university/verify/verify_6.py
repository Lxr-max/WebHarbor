#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--6.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # University News category count (43) -> MacArthur search (3 results
    # unfiltered, 1 result if the search is run with the University News
    # category filter the task set up still applied — both are honest paths
    # for the task text, so the count gate accepts either) ->
    # Song Lin story (Chemistry, $800,000 over five years, September 29 2026,
    # Adam Hadhazy) -> Health & Medicine topic (22, newest "Why changing
    # California's school menus may be difficult" September 28 2026 by Erin
    # Digitale) -> Siebel Scholars story (September 21 2026, Alex Kekauoha,
    # main topic Awards & Honors).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"category=University",
        r"q=MacArthur",
        r"/news/song-lin-macarthur-fellowship",
        r"topic=Health",
        r"q=Siebel",
    ])
    check_answer_number(judge, answer, "univ_news_count", 43)
    check_answer_number_any(judge, answer, "macarthur_results", [1, 3])
    check_answer_phrase(judge, answer, "fellow_name", "Song Lin")
    check_answer_phrase(judge, answer, "fellow_dept", "Chemistry")
    check_answer_price(judge, answer, "award_amount", "800,000")
    check_answer_phrase(judge, answer, "award_paid", "over five years")
    check_answer_phrase(judge, answer, "pub_date", "September 29, 2026")
    check_answer_phrase(judge, answer, "writer", "Adam Hadhazy")
    check_answer_number(judge, answer, "hm_topic_count", 22)
    check_answer_phrase(judge, answer, "hm_newest_title", "Why changing California")
    check_answer_phrase(judge, answer, "hm_newest_date", "September 28, 2026")
    check_answer_phrase(judge, answer, "hm_newest_writer", "Erin Digitale")
    check_answer_phrase(judge, answer, "siebel_title", "18 Stanford students named Siebel Scholars")
    check_answer_phrase(judge, answer, "siebel_date", "September 21, 2026")
    check_answer_phrase(judge, answer, "siebel_writer", "Alex Kekauoha")
    check_answer_phrase(judge, answer, "siebel_topic", "Awards & Honors")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
