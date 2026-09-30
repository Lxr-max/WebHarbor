#!/usr/bin/env python3
"""Deterministic verifier for Disney--14 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.
    r2 note: the task now uses the upstream official casing "Magic in the
    Stars" exactly as the schedule filter lists it.

Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "doi_schedule", r"""/live-shows/disney-on-ice"""),
    check_visited_path(judge, traj, "mits_filter", r"""/live-shows/disney-on-ice\?[^\" ]*show=Magic\+in\+the\+Stars"""),
    check_visited_path(judge, traj, "ca_search", r"""/live-shows/disney-on-ice\?[^\" ]*q=CA"""),
    check_visited_path(judge, traj, "city_sort", r"""/live-shows/disney-on-ice\?[^\" ]*sort=city"""),
    check_visited_path(judge, traj, "albany_detail", r"""/live-shows/disney-on-ice/121030"""),
    check_visited_path(judge, traj, "booking", r"""/live-shows/disney-on-ice/121030/book"""),
    check_visited_path(judge, traj, "ticket_confirmed", r"""/tickets/TK"""),
    # -- answer ground truth --
    check_answer_number(judge, answer, "mits_count", 15)
    check_answer_number(judge, answer, "ca_count", 8)
    check_answer_phrase(judge, answer, "first_city", "Albany, NY")
    check_answer_phrase(judge, answer, "venue", "MVP Arena")
    check_answer_number(judge, answer, "performances", 4)
    check_answer_phrase(judge, answer, "booked_day", "Jan 21, 2027")
    check_answer_regex(judge, answer, "booked_time", r"(?<![0-9:])7:00 pm")
    check_answer_money(judge, answer, "ticket_total", 70.00)
    check_answer_regex(judge, answer, "confirmation", r"TK[0-9A-F]{7}")

    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='ice.first@example.com' "
        "AND event_id='121030' AND qty=2 AND total=70.0 AND day='Jan 21, 2027' AND time='7:00 pm'",
        (), "ticket_row")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
