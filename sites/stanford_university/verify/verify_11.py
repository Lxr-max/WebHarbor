#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--11.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Robin Li and Melissa Ma Science Library ((650) 723-1528, 376 Lomita
    # Drive) -> Green Library (Library & circulation: Sunday 12p-12a, Friday
    # 8a-12a, (650) 723-1493) -> Music Library (650-723-1211) -> east search
    # -> East Asia Library (Lathrop Library..., research subject) ->
    # philosophy search (1 match) -> Tanner Memorial Library of Philosophy
    # (location "Main Quad, first floor of Building 90, Room 91F" —
    # re-captured from philosophy.stanford.edu per the r2 fix).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/libraries/robin-li-and-melissa-ma-science-library",
        r"/libraries/cecil-h-green-library",
        r"/libraries/music-library",
        r"q=east",
        r"/libraries/east-asia-library",
        r"q=philosophy",
    ])
    check_answer_phrase(judge, answer, "robinli_phone", "(650) 723-1528")
    check_answer_phrase(judge, answer, "robinli_location", "376 Lomita Drive")
    check_answer_phrase(judge, answer, "green_sunday_hours", "12p-12a")
    check_answer_phrase(judge, answer, "green_friday_hours", "8a-12a")
    check_answer_phrase(judge, answer, "green_phone", "(650) 723-1493")
    check_answer_phrase(judge, answer, "music_phone", "650-723-1211")
    check_answer_phrase(judge, answer, "east_asia_location", "Lathrop Library")
    check_answer_any(judge, answer, "east_asia_subject",
                     ["Chinese studies", "Japanese studies", "Korean studies"])
    check_answer_number(judge, answer, "philosophy_search_count", 1)
    check_answer_phrase(judge, answer, "philosophy_library", "Tanner")
    check_answer_phrase(judge, answer, "philosophy_location", "Main Quad, first floor of Building 90, Room 91F")
    check_read_only(judge, initial, after)

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
