#!/usr/bin/env python3
"""Deterministic verifier for dblp--10.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_10.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--10"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_watchlist", r"/account/watchlist")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=learning")
    check_visited_path(judge, traj, "nav_tmlr", r"/db/journals/tmlr/index\.html")
    check_visited_path(judge, traj, "nav_volume", r"/db/journals/tmlr/tmlr2026")
    check_visited_path(judge, traj, "nav_first_rec", r"/rec/journals/tmlr/AKMC26")
    check_visited_path(judge, traj, "nav_author", r"/pid/423/5020")
    check_visited_path(judge, traj, "nav_after_logout", r"/authn/login\?next=%2Faccount%2Fwatchlist")
    check_answer_count_at_least(judge, answer, "seed_venues", ["ACM SIGMOD Conference (SIGMOD)", "Proceedings of the VLDB Endowment", "Proceedings of the ACM on Management of Data (PACMMOD)"], 3)
    check_answer_count_at_least(judge, answer, "seed_venue_counts", ["726", "1384", "1160"], 3)
    check_answer_number(judge, answer, "tmlr_records", 2747)
    check_answer_number(judge, answer, "tmlr_volumes", 2)
    check_answer_phrase(judge, answer, "tmlr_top_author", "Wenhu Chen")
    check_answer_number(judge, answer, "tmlr_top_count", 10)
    check_answer_phrase(judge, answer, "tmlr_watched", "Transactions on Machine Learning Research")
    check_answer_phrase(judge, answer, "vol_title", "Transactions on Machine Learning Research, Volume 2026")
    check_answer_number(judge, answer, "vol_records", 1315)
    check_answer_phrase(judge, answer, "first_title", "Proper Orthogonal Decomposition for Scalable Training of Graph Neural Networks.")
    check_answer_phrase(judge, answer, "first_mdate", "2026-02-08")
    check_answer_number(judge, answer, "author_pubs", 2)
    check_answer_any(judge, answer, "after_logout", ["login", "log in"])
    # bob (user 2): +1 TMLR venue watch (venue 18); history rows for 'learning'
    added, removed, _ = _diff(initial, after, "watch_venues")
    if len(added) == 1 and added[0][2] == 18 and not removed:
        judge.ok("watch_venues_delta", "TMLR (venue 18) added")
    else:
        judge.fail("watch_venues_delta", f"added {added} removed {removed}")
    added, _, _ = _diff(initial, after, "search_history")
    bad = [r for r in added if r[1] != 2 or r[2] != "learning" or r[4] != 13637]
    if not (1 <= len(added) <= 3) or bad:
        judge.fail("history_added", f"unexpected history rows: {added}")
    else:
        judge.ok("history_added", f"{len(added)} row(s)")
    check_only_tables_changed(judge, initial, after,
                              {"watch_venues", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
