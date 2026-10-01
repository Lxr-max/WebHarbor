#!/usr/bin/env python3
"""Deterministic verifier for dblp--13.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_13.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--13"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_history", r"/account/history")
    check_visited_path(judge, traj, "nav_publ_search1", r"/search/publ\?q=deep\+learning")
    check_visited_path(judge, traj, "nav_publ_search2", r"/search/publ\?q=index")
    check_visited_path(judge, traj, "nav_publ_search3", r"/search/publ\?q=sql")
    check_visited_path(judge, traj, "nav_author_search", r"/search/author\?q=zhang")
    check_visited_path(judge, traj, "nav_first_profile", r"/pid/z/AidongZhang")
    check_answer_count_at_least(judge, answer, "seed_history", ["embedding", "language model", "summarization", "retrieval", "question answering"], 5)
    check_answer_phrase(judge, answer, "cleared", "search history is empty")
    check_answer_number(judge, answer, "count_deep_learning", 466)
    check_answer_number(judge, answer, "count_index", 227)
    check_answer_number(judge, answer, "count_sql", 96)
    check_answer_number(judge, answer, "history_total", 3)
    check_answer_number(judge, answer, "zhang_matches", 3639)
    check_answer_number(judge, answer, "zhang_first_pubs", 12)
    # dana (user 4): history cleared first, then exactly the three publication
    # searches plus one 'zhang' author search (one search action = one entry)
    rows = list(after.execute(
        "SELECT query, search_type, hits FROM search_history WHERE user_id=4"))
    expected = {("deep learning", "publ", 466),
                 ("index", "publ", 227),
                 ("sql", "publ", 96),
                 ("zhang", "author", 3639)}
    if len(rows) == 4 and {(r[0], r[1], r[2]) for r in rows} == expected:
        judge.ok("history_final", f"{sorted(expected)}")
    else:
        judge.fail("history_final", f"expected 4 rows {sorted(expected)}, got {rows}")
    check_only_tables_changed(judge, initial, after, {"search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
