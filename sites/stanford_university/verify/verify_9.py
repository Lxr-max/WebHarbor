#!/usr/bin/env python3
"""Deterministic verifier for Stanford University--9.

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-stanford-review, seed
sha256 40897e025003956e34f418eb213d7ea786775d342cabcbeba560b5767059d65c, with
every hardcoded fact cross-checked against the frozen seed database) — never
read from tasks.jsonl.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Stanford University--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    # Bob login -> saved events (Trust and Safety Research Conference) ->
    # December 2026 filter (60, first Salvatierra Lecture) -> save (2) ->
    # conference search -> remove Trust and Safety Research Conference (1).
    check_visited_all(judge, traj, "nav_surfaces", [
        r"/login",
        r"/saved-events",
        r"month=2026-12",
        r"/events/53728866418041",
        r"/events\?q=conference",
        r"/events/53074254797631",
    ])
    check_answer_phrase(judge, answer, "bob_saved_events", "Trust and Safety Research Conference")
    check_answer_number(judge, answer, "bob_saved_count", 1)
    check_answer_number(judge, answer, "dec_count", 60)
    check_answer_phrase(judge, answer, "dec_first_title", "Salvatierra Lecture")
    check_answer_number(judge, answer, "saved_after_add", 2)
    check_answer_number(judge, answer, "saved_final_count", 1)
    check_answer_phrase(judge, answer, "saved_final_titles", "Salvatierra Lecture")
    check_answer_absent(judge, answer, "removed_tsrc", "Trust and Safety Research Conference, Salvatierra")
    check_only_tables_changed(judge, initial, after, {"saved_events"})
    check_rows_added(judge, initial, after, "saved_events",
                     [[None, 2, 53728866418041, None, None]], "saved_add_bob_salvatierra")
    check_rows_removed(judge, initial, after, "saved_events",
                       [[None, 2, 53074254797631, None, None]], "saved_remove_bob_tsrc")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
