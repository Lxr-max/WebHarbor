#!/usr/bin/env python3
"""Deterministic verifier for dblp--11.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_11.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--11"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_saved_searches", r"/account/saved-searches")
    check_visited_path(judge, traj, "nav_qa_run", r"/search/publ\?q=question\+answering")
    check_visited_path(judge, traj, "nav_lm_search", r"q=language\+model")
    check_visited_path(judge, traj, "nav_lm_publ", r"/search/publ\?q=language\+model")
    check_visited_path(judge, traj, "nav_first_hit", r"/rec/conf/acl/AbdallahAPJ26")
    check_visited_path(judge, traj, "nav_saved_papers", r"/account/papers")
    check_answer_phrase(judge, answer, "seed_qa", "question answering")
    check_answer_number(judge, answer, "qa_count", 160)
    check_answer_number(judge, answer, "lm_count", 2620)
    check_answer_phrase(judge, answer, "saved_lm", "language model")
    check_answer_number(judge, answer, "run_count", 2620)
    check_answer_phrase(judge, answer, "first_doi", "10.18653/v1/2026.acl-long.153")
    check_answer_phrase(judge, answer, "collection_landed", "My Library")
    # dana (user 4): +1 'language model' saved search, -1 QA search,
    # +1 saved paper in My Library, history rows for QA / language model
    added, removed, _ = _diff(initial, after, "saved_searches")
    ok_add = len(added) == 1 and added[0][2] == "language model" \
        and added[0][3] == "publ"
    ok_rm = len(removed) == 1 and removed[0][2] == "question answering"
    if ok_add and ok_rm:
        judge.ok("saved_searches_delta", "+language model -question answering")
    else:
        judge.fail("saved_searches_delta", f"added {added} removed {removed}")
    added, _, _ = _diff(initial, after, "saved_papers")
    if len(added) == 1 and added[0][2] == 150 and added[0][3] == "My Library":
        judge.ok("saved_papers_added", "first lm hit saved to My Library")
    else:
        judge.fail("saved_papers_added", f"got {added}")
    added, _, _ = _diff(initial, after, "search_history")
    allowed = {("question answering", 160), ("language model", 2620)}
    bad = [r for r in added
           if r[1] != 4 or (r[2], r[4]) not in allowed]
    if not (2 <= len(added) <= 6) or bad:
        judge.fail("history_added", f"unexpected history rows: {added}")
    else:
        judge.ok("history_added", f"{len(added)} row(s)")
    check_only_tables_changed(judge, initial, after,
                              {"saved_searches", "saved_papers", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
