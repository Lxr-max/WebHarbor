#!/usr/bin/env python3
"""Deterministic verifier for Red Bull--0 (red_bull).

Ground truth below is HARDCODED (frozen from the reviewer's two independent
honest Playwright rounds on the review container wh-red-bull-review, seed md5
2e3f7d1ce9c852f434d394942fe9fa57, with every hardcoded fact cross-checked
against the frozen seed database) — never read from tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Red Bull--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)

    check_visited_all(judge, traj, "nav_surfaces", [
        r"/events($|\?)",
        r"/events/red-bull-foam-wreckers-virginia-beach$",
        r"/events/red-bull-foam-wreckers-virginia-beach/faqs",
        r"/events/red-bull-foam-wreckers-virginia-beach/schedule",
        r"/events/red-bull-foam-wreckers-virginia-beach/register$",
        r"/events/red-bull-foam-wreckers-virginia-beach/register/confirmation/RB[A-Z0-9]+",
        r"/events/red-bull-foam-wreckers-narragansett$",
        r"/event-series/red-bull-foam-wreckers$",
    ])
    check_answer_any(judge, answer, "faq_softboards", ["soft-boards", "soft-boards are allowed", "soft-top"])
    check_answer_phrase(judge, answer, "faq_spectators", "free and open to the public")
    check_answer_phrase(judge, answer, "checkin", "Check In 9a - 10a")
    check_answer_money(judge, answer, "entry_fee", 20)
    check_answer_regex(judge, answer, "reg_code", r"RB[A-Z0-9]{8}")
    check_answer_phrase(judge, answer, "ri_venue", "Narragansett Town Beach")
    # r2 re-anchor: the Foam Wreckers series page leg (last stop + its date)
    check_answer_phrase(judge, answer, "series_last_stop", "San Diego")
    check_answer_phrase(judge, answer, "series_last_date", "November 7, 2026")
    check_only_tables_changed(judge, initial, after, {"event_registrations"})
    check_rows_added(judge, initial, after, "event_registrations", [
        [None, "rx:^RB[A-Z0-9]{8}$", None, 3, "Red Bull Foam Wreckers - Northeast Region",
         "Casey", "Rider", "casey.rider@example.com", 20.0, "USD", "confirmed", None],
    ], "registration_row")
    # the code in the answer must be the code in the DB
    import re as _re
    codes = [r[0] for r in after.execute(
        "SELECT registration_code FROM event_registrations WHERE email='casey.rider@example.com'")]
    if codes and _re.search(rf"{codes[0]}", answer):
        judge.ok("answer_code_matches_db", codes[0])
    else:
        judge.fail("answer_code_matches_db", f"answer lacks DB code {codes}")



if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
