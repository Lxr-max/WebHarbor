#!/usr/bin/env python3
"""Deterministic verifier for dblp--8.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_8.py --run_dir DIR [--initial_db P] [--after_db P]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (
    check_answer_absent, check_answer_any, check_answer_count_at_least,
    check_answer_number, check_answer_number_absent, check_answer_number_near,
    check_answer_number_absent, check_answer_ordered,
    check_answer_phrase, check_answer_regex, check_read_only,
    check_rows_added, check_rows_changed, check_rows_removed,
    check_only_tables_changed, check_screenshots, check_seed_contract,
    check_step_action, check_trajectory_identity, check_visited_all,
    check_visited_any, check_visited_path, final_answer,
    run_verifier, TABLES, _diff,
)

TASK_ID = "dblp--8"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_register", r"/authn/register")
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=side\+channel|/search/publ\?q=side\+channel")
    check_visited_path(judge, traj, "nav_hit1_record", r"/rec/conf/sp/LiYHCHW26")
    check_visited_path(judge, traj, "nav_hit2_record", r"/rec/journals/tifs/SpolaorSMZYCH26")
    check_visited_path(judge, traj, "nav_saved_papers", r"/account/papers")
    check_answer_number(judge, answer, "count", 12)
    check_answer_phrase(judge, answer, "collection_name", "Security reading")
    check_answer_phrase(judge, answer, "hit1_title", "PrintSpy: Pixel-Level Eavesdropping on Commodity Laser Printers via Electromagnetic Side Channels.")
    check_answer_phrase(judge, answer, "hit2_title", "PowerEar: An Audio Eavesdropping Attack on Mobile Devices Through USB Power Side Channel.")
    check_answer_number(judge, answer, "export_entries", 2)
    check_answer_phrase(judge, answer, "first_entry_type", "inproceedings")
    check_answer_any(judge, answer, "remaining_title", ["PrintSpy: Pixel-Level Eavesdropping on Commodity Laser Printers via Electromagnetic Side Channels.", "PowerEar: An Audio Eavesdropping Attack on Mobile Devices Through USB Power Side Channel."])
    check_step_action(judge, traj, "nav_export_download", "download"),
    # stateful: one new registered user + one surviving Security reading row
    added, _, _ = _diff(initial, after, "users")
    if len(added) != 1:
        judge.fail("users_added", f"expected 1 added user, got {len(added)}: {added}")
    else:
        u = added[0]
        ok = (u[4] == 0 and u[7] == "2026-09-30" and u[1] != "" and u[2] != "")
        (judge.ok if ok else judge.fail)(
            "users_added", f"new user row {u[:3]}")
    added, _, _ = _diff(initial, after, "saved_papers")
    want_pubs = {24041, 31863}
    if len(added) != 1 or added[0][2] not in want_pubs \
            or added[0][3] != "Security reading":
        judge.fail("saved_papers_added",
                   f"expected 1 Security reading row (either hit), got {added}")
    else:
        judge.ok("saved_papers_added", f"{added[0][2]} in Security reading")
    added, _, _ = _diff(initial, after, "search_history")
    bad = [r for r in added
           if r[2] != "side channel" or r[3] != "publ" or r[4] != 12]
    if not (1 <= len(added) <= 4) or bad:
        judge.fail("history_added", f"unexpected history rows: {added}")
    else:
        judge.ok("history_added", f"{len(added)} side-channel row(s)")
    check_only_tables_changed(judge, initial, after,
                              {"users", "saved_papers", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
