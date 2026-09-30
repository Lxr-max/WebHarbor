#!/usr/bin/env python3
"""Deterministic verifier for Disney--15 (disney).

Ground truth below is HARDCODED from the reviewer's independent Playwright
honest-path walk on the r2 review container (wh-disney-r2-review, seed md5
9f231a5a…) — never read from tasks.jsonl.

Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "Disney--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = (traj.get("final_answer") or "")

    # -- navigation gates (anti knowledge-shortcut) --
    check_visited_path(judge, traj, "kent_search", r"""/live-shows/disney-on-ice\?[^\" ]*q=Kent"""),
    check_visited_path(judge, traj, "kent_detail", r"""/live-shows/disney-on-ice/120960"""),
    check_visited_path(judge, traj, "booking", r"""/live-shows/disney-on-ice/120960/book[^\" ]*day=Oct\+24|/live-shows/disney-on-ice/120960/book"""),
    check_visited_path(judge, traj, "ticket_confirmed", r"""/tickets/TK"""),
    check_visited_path(judge, traj, "jii_filter", r"""/live-shows/disney-on-ice\?[^\" ]*show=Jump\+In!"""),
    check_visited_path(judge, traj, "jii_city_sort", r"""/live-shows/disney-on-ice\?[^\" ]*sort=city[^\" ]*show=Jump\+In!|/live-shows/disney-on-ice\?[^\" ]*show=Jump\+In![^\" ]*sort=city"""),
    # -- answer ground truth --
    check_answer_phrase(judge, answer, "venue", "accesso ShoWare Center")
    check_answer_phrase(judge, answer, "date_range", "Oct 22-25, 2026")
    check_answer_phrase(judge, answer, "booked_day", "Oct 24, 2026")
    check_answer_regex(judge, answer, "booked_time", r"(?<![0-9:])11:00 am")
    check_answer_money(judge, answer, "ticket_total", 105.00)
    check_answer_regex(judge, answer, "confirmation", r"TK[0-9A-F]{7}")
    check_answer_number(judge, answer, "jii_count", 16)
    check_answer_phrase(judge, answer, "jii_first_city", "Anaheim, CA")
    check_answer_phrase(judge, answer, "jii_first_venue", "Honda Center")

    check_only_tables_changed(judge, initial, after, {"ticket_orders"})
    check_rows_added(judge, initial, after, "ticket_orders", 1)
    check_row_matches(judge, after,
        "SELECT 1 FROM ticket_orders WHERE email='skate.fan@example.com' "
        "AND event_id='120960' AND qty=3 AND total=105.0 AND day='Oct 24, 2026' AND time='11:00 am'",
        (), "ticket_row")

if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
