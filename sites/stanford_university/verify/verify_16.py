#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--16.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Homepage newest story (featured unit Stanford School of Humanities &
    # Sciences, main topic Awards & Honors — detail-page facts; the homepage
    # card shows neither) -> upcoming first event Climber Coffee (2026-10-01,
    # Arrillaga Outdoor Education & Recreation Center) -> dana login via
    # in-page link -> save -> saved list shows 2 -> academic calendar
    # (Autumn September 22; Summer 44 entries) -> libraries classics search
    # (1 match, Classics Library, (650) 723-0479).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/news/song-lin-macarthur-fellowship",
        r"when=upcoming",
        r"/events/47490479889681",
        r"/login",
        r"/saved-events",
        r"/academic-calendar",
        r"quarter=summer",
        r"/libraries",
        r"q=classics",
    ])
    check_answer_phrase(judge, answer, "newest_story_title", "Stanford chemist Song Lin receives MacArthur Fellowship")
    check_answer_phrase(judge, answer, "newest_story_featured_unit", "Stanford School of Humanities & Sciences")
    check_answer_phrase(judge, answer, "newest_story_main_topic", "Awards & Honors")
    check_answer_phrase(judge, answer, "upcoming_title", "Climber Coffee")
    check_answer_phrase(judge, answer, "upcoming_date", "2026-10-01")
    check_answer_phrase(judge, answer, "upcoming_location", "Arrillaga Outdoor Education & Recreation Center")
    check_answer_number(judge, answer, "dana_saved_count", 2)
    check_answer_phrase(judge, answer, "autumn_instruction_begins", "September 22 (Tue)")
    check_answer_number(judge, answer, "summer_entries", 44)
    check_answer_number(judge, answer, "classics_count", 1)
    check_answer_phrase(judge, answer, "classics_first_library", "Classics Library")
    check_answer_phrase(judge, answer, "classics_first_phone", "(650) 723-0479")
    check_only_tables_changed(judge, initial, after, {"saved_events"})
    check_rows_added(judge, initial, after, "saved_events",
                     [[None, 4, 47490479889681, None, None]], "saved_add_dana_climber")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
