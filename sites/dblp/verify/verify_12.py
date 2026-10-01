#!/usr/bin/env python3
"""Deterministic verifier for dblp--12.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_12.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--12"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_saved_papers", r"/account/papers")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=fuzzing|/search/publ\?q=fuzzing")
    check_visited_path(judge, traj, "nav_hit1", r"/rec/conf/sp/AndroutsopoulosB26")
    check_visited_path(judge, traj, "nav_hit2", r"/rec/conf/sp/BennettTSETB26")
    check_visited_path(judge, traj, "nav_watchlist", r"/account/watchlist")
    check_answer_phrase(judge, answer, "seed_collection", "My Library")
    check_answer_number(judge, answer, "count", 54)
    check_answer_phrase(judge, answer, "new_collection", "Audit queue")
    check_answer_number(judge, answer, "my_library_entries", 4)
    check_answer_number(judge, answer, "audit_queue_entries", 2)
    check_answer_any(judge, answer, "audit_remaining_title", ["Fizzle: A Framework for Deterministic and Reproducible Network Fuzzing.", "deepSURF: Detecting Memory Safety Vulnerabilities in Rust Through Fuzzing LLM-Augmented Harnesses."])
    check_answer_count_at_least(judge, answer, "watched_venues", ["IEEE Symposium on Security and Privacy (SP)", "IEEE Transactions on Information Forensics and Security"], 2)
    check_step_action(judge, traj, "nav_export_downloads", "download"),
    # carol (user 3): +1 surviving Audit queue row (either fuzzing hit),
    # history rows for 'fuzzing'
    added, _, _ = _diff(initial, after, "saved_papers")
    want = {23721, 23744}
    if len(added) == 1 and added[0][1] == 3 and added[0][2] in want \
            and added[0][3] == "Audit queue":
        judge.ok("saved_papers_added", f"{added[0][2]} in Audit queue")
    else:
        judge.fail("saved_papers_added", f"got {added}")
    added, _, _ = _diff(initial, after, "search_history")
    bad = [r for r in added if r[1] != 3 or r[2] != "fuzzing" or r[4] != 54]
    if not (1 <= len(added) <= 3) or bad:
        judge.fail("history_added", f"unexpected history rows: {added}")
    else:
        judge.ok("history_added", f"{len(added)} fuzzing row(s)")
    check_only_tables_changed(judge, initial, after,
                              {"saved_papers", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
