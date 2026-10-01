#!/usr/bin/env python3
"""Deterministic verifier for dblp--14.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_14.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--14"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_profile", r"/account/profile")
    check_visited_path(judge, traj, "nav_dashboard", r"/account")
    check_visited_path(judge, traj, "nav_watchlist", r"/account/watchlist")
    check_visited_path(judge, traj, "nav_papers", r"/account/papers")
    check_visited_path(judge, traj, "nav_saved_searches", r"/account/saved-searches")
    check_answer_phrase(judge, answer, "profile_email", "alice.j@test.com")
    check_answer_phrase(judge, answer, "member_since", "2026-09-01")
    check_answer_phrase(judge, answer, "seed_display_name", "Alice Johnson")
    check_answer_phrase(judge, answer, "seed_affiliation", "Stanford University")
    check_answer_phrase(judge, answer, "updated_affiliation", "MIT CSAIL")
    check_answer_phrase(judge, answer, "updated_interests", "graph learning and attention")
    check_answer_number(judge, answer, "dashboard_authors", 3)
    check_answer_number(judge, answer, "dashboard_venues", 2)
    check_answer_count_at_least(judge, answer, "recent_searches", ["attention", "transformer", "graph neural network"], 2)
    check_answer_count_at_least(judge, answer, "watchlist_authors", ["Dacheng Tao", "Li Shen 0008", "Lei Bai 0001"], 3)
    check_answer_count_at_least(judge, answer, "collections", ["My Library"], 1)
    check_answer_count_at_least(judge, answer, "collection_counts", ["6"], 1)
    check_answer_count_at_least(judge, answer, "saved_searches", ["graph neural network", "transformer"], 2)
    check_answer_phrase(judge, answer, "final_affiliation", "Stanford University")
    check_answer_phrase(judge, answer, "final_interests", "graph learning and attention")
    # alice (user 1): only her user row changes; display name edited away from
    # the seed value, affiliation restored to Stanford University, interests set
    changed_rows = _diff(initial, after, "users")[2]
    if len(changed_rows) == 1 and changed_rows[0][0][0] == 1:
        judge.ok("users_delta", "alice row updated")
    else:
        judge.fail("users_delta", f"unexpected user changes: {changed_rows}")
    row = list(after.execute(
        "SELECT display_name, affiliation, research_interests FROM users WHERE id=1"))[0]
    if (row[0] != "Alice Johnson" and
            row[1] == "Stanford University" and
            row[2] == "graph learning and attention"):
        judge.ok("profile_final", f"{row}")
    else:
        judge.fail("profile_final", f"got {row}")
    check_only_tables_changed(judge, initial, after, {"users"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
