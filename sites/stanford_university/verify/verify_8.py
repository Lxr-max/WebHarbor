#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--8.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Lecture search (29) -> Hoover Shultz Memorial Lecture (2026-10-01,
    # Hoover Institution - George P. Shultz Building, Ticketed) ->
    # November 2026 (60, first "Stanford Energy Seminar | The US Energy
    # Transition..." at Shriram Center) -> upcoming+seminar (91, first row
    # 2026-10-01) -> concert search (36, first "Stanford Medicine Orchestra
    # with violinist Stella Chen.", address 471 Lagunita Drive).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"q=lecture",
        r"/events/54101567783190",
        r"month=2026-11",
        r"when=upcoming",
        r"q=seminar",
        r"q=concert",
    ])
    check_answer_number(judge, answer, "lecture_count", 29)
    check_answer_phrase(judge, answer, "hoover_date", "2026-10-01")
    check_answer_phrase(judge, answer, "hoover_location", "Hoover Institution - George P. Shultz Building")
    check_answer_any(judge, answer, "hoover_free", ["Ticketed", "not free", "paid"])
    check_answer_absent(judge, answer, "hoover_free_trip", "free of charge")
    check_answer_number(judge, answer, "nov_count", 60)
    check_answer_phrase(judge, answer, "nov_first_title", "Stanford Energy Seminar")
    check_answer_phrase(judge, answer, "nov_first_location", "Shriram Center")
    check_answer_number(judge, answer, "upcoming_seminar_count", 91)
    check_answer_phrase(judge, answer, "first_upcoming_seminar_date", "2026-10-01")
    check_answer_number(judge, answer, "concert_count", 36)
    check_answer_phrase(judge, answer, "concert_first_title", "Stanford Medicine Orchestra")
    check_answer_phrase(judge, answer, "concert_first_address", "471 Lagunita Drive")
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
