#!/usr/bin/env python3
"""Deterministic verifier for Disney--16 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 redesign: the task is one real multi-city planning chain measured
    at 18 honest atomic steps by the r2 reviewer's own two-round
    Chromium walks (the per-performance Buy Tickets link prefills
    day+time; changing the prefilled 1:00 pm to the task-required
    5:00 pm performance is a genuinely required step).

Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent,
    check_answer_any,
    check_answer_count_at_least,
    check_answer_number,
    check_answer_number_absent,
    check_answer_ordered,
    check_answer_money,
    check_answer_phrase,
    check_answer_regex,
    check_only_tables_changed,
    check_read_only,
    check_row_matches,
    check_rows_added,
    check_screenshots,
    check_seed_contract,
    check_trajectory_identity,
    check_visited_all,
    check_visited_any,
    check_visited_path,
    run_verifier
)

TASK_ID = "Disney--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "live_shows", r"""/live-shows($|\?)"""),
    check_visited_path(judge, traj, "doi_schedule", r"""/live-shows/disney-on-ice"""),
    check_visited_path(judge, traj, "fyh_filter", r"""/live-shows/disney-on-ice\?[^\" ]*show=Find\+Your\+Hero"""),
    check_visited_path(judge, traj, "tx_search", r"""/live-shows/disney-on-ice\?[^\" ]*q=TX"""),
    check_visited_path(judge, traj, "city_sort", r"""/live-shows/disney-on-ice\?[^\" ]*sort=city"""),
    check_visited_path(judge, traj, "laredo_detail", r"""/live-shows/disney-on-ice/120991"""),
    check_visited_path(judge, traj, "booking", r"""/live-shows/disney-on-ice/120991/book"""),
    check_visited_path(judge, traj, "ticket_confirmed", r"""/tickets/TK"""),
    check_visited_path(judge, traj, "mof_filter", r"""/live-shows/disney-on-ice\?[^\" ]*show=Magic\+of\+Family"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "broadway_musicals", 3)
    check_answer_number(judge, answer, "events_total", 89)
    check_answer_number(judge, answer, "fyh_count", 18)
    check_answer_number(judge, answer, "tx_count", 5)
    check_answer_phrase(judge, answer, "laredo_venue", "Sames Auto Arena")
    check_answer_phrase(judge, answer, "laredo_dates", "Nov 20-22, 2026")
    check_answer_phrase(judge, answer, "booked_day", "Nov 22, 2026")
    check_answer_regex(judge, answer, "booked_time", r"(?<![0-9:])5:00 pm")
    check_answer_money(judge, answer, "ticket_total", 70.00)
    check_answer_regex(judge, answer, "confirmation", r"TK[0-9A-F]{7}")
    check_answer_number(judge, answer, "mof_count", 19)

    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='laredo.ice@example.com' "
        "AND event_id='120991' AND qty=2 AND total=70.0 AND day='Nov 22, 2026' AND time='5:00 pm'",
        (), "ticket_row")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
