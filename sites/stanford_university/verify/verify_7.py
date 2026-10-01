#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--7.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # R&S + H&M filter (20, newest "Why changing California's school menus
    # may be difficult" September 28 2026 by Erin Digitale) -> clear (newest
    # overall Song Lin September 29 2026) -> democracy search (10, newest
    # "Lara Tiedens appointed as CASBS director", Institutional News) ->
    # On Campus filter (42, newest "President Levin and student leaders on
    # the year ahead", main topic Events) -> Student Experience count (32).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"category=Research",
        r"topic=Health",
        r"/news\?q=democracy",
        r"category=Student",
    ])
    check_answer_number(judge, answer, "rs_hm_count", 20)
    check_answer_phrase(judge, answer, "rs_hm_newest_title", "Why changing California")
    check_answer_phrase(judge, answer, "rs_hm_newest_date", "September 28, 2026")
    check_answer_phrase(judge, answer, "rs_hm_newest_writer", "Erin Digitale")
    check_answer_phrase(judge, answer, "newest_overall_title", "Stanford chemist Song Lin receives MacArthur Fellowship")
    check_answer_phrase(judge, answer, "newest_overall_date", "September 29, 2026")
    check_answer_number(judge, answer, "democracy_count", 10)
    check_answer_phrase(judge, answer, "democracy_newest_title", "Lara Tiedens appointed as CASBS director")
    check_answer_phrase(judge, answer, "democracy_newest_category", "Institutional News")
    check_answer_number(judge, answer, "on_campus_count", 42)
    check_answer_phrase(judge, answer, "on_campus_newest_title", "President Levin and student leaders on the year ahead")
    check_answer_phrase(judge, answer, "on_campus_newest_topic", "Events")
    check_answer_number(judge, answer, "student_exp_count", 32)
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
