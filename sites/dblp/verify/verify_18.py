#!/usr/bin/env python3
"""Deterministic verifier for dblp--18.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_18.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--18"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=learned\+index")
    check_visited_path(judge, traj, "nav_record", r"/rec/journals/pacmmod/ChenC26")
    check_visited_path(judge, traj, "nav_venue_search", r"/search\?q=neural")
    check_visited_path(judge, traj, "nav_nips", r"/db/conf/nips/index\.html")
    check_visited_path(judge, traj, "nav_papers", r"/account/papers")
    check_visited_path(judge, traj, "nav_watchlist", r"/account/watchlist")
    check_answer_number(judge, answer, "count", 36)
    check_answer_phrase(judge, answer, "first_ee_doi", "10.1145/3802080")
    check_answer_phrase(judge, answer, "first_venue", "Proc. ACM Manag. Data")
    check_answer_number(judge, answer, "nips_records", 5823)
    check_answer_phrase(judge, answer, "nips_top_author", "Dacheng Tao")
    check_answer_number(judge, answer, "nips_top_count", 23)
    check_answer_count_at_least(judge, answer, "db_reading_list", ["Advancing Fact Attribution for Query Answering: Aggregate Queries and Novel Algorithms.", "Efficient Query Repair for Aggregate Constraints.", "Exploring Exploratory Querying.", "Environmental Footprints of Query Processing: A Vision for Sustainable Database Architectures.", "QBAT: Model-based Query Budget Autotuner for Clustering-based Approximate Nearest Neighbor Search.", "LINE: A Learned Index with Group-Enhanced Leaves and Cache-Optimized Inner Tree."], 6)
    check_answer_number(judge, answer, "export_entries", 6)
    check_answer_count_at_least(judge, answer, "watched_venues", ["ACM SIGMOD Conference (SIGMOD)", "Proceedings of the VLDB Endowment", "Proceedings of the ACM on Management of Data (PACMMOD)", "Conference on Neural Information Processing Systems (NeurIPS)"], 4)
    check_answer_count_at_least(judge, answer, "remaining_venues", ["ACM SIGMOD Conference (SIGMOD)", "Proceedings of the ACM on Management of Data (PACMMOD)", "Conference on Neural Information Processing Systems (NeurIPS)"], 3)
    # bob (user 2): +1 saved paper in 'DB reading list' (the learned-index
    # first hit, publication 28125), +1 NeurIPS watch venue (venue 6, a real
    # add — NeurIPS is not in bob's seed), -1 seeded PVLDB watch venue
    # (venue 16), history rows for the two queries
    added, _, _ = _diff(initial, after, "saved_papers")
    if len(added) == 1 and added[0][1] == 2 and added[0][2] == 28125 \
            and added[0][3] == "DB reading list":
        judge.ok("saved_papers_added", "learned-index hit saved")
    else:
        judge.fail("saved_papers_added", f"got {added}")
    added, removed, _ = _diff(initial, after, "watch_venues")
    ok_add = len(added) == 1 and added[0][1] == 2 and added[0][2] == 6
    ok_rm = len(removed) == 1 and removed[0][1] == 2 and removed[0][2] == 16
    if ok_add and ok_rm:
        judge.ok("watch_venues_delta", "+NeurIPS (6) -PVLDB (16)")
    else:
        judge.fail("watch_venues_delta", f"added {added} removed {removed}")
    added, _, _ = _diff(initial, after, "search_history")
    ok_hist = all(r[1] == 2 and r[3] == "publ" for r in added) and \
        {r[2] for r in added} == {"learned index", "neural"}
    if ok_hist and 2 <= len(added) <= 4:
        judge.ok("history_added", f"{len(added)} row(s)")
    else:
        judge.fail("history_added", f"unexpected history rows: {added}")
    check_only_tables_changed(judge, initial, after,
                              {"saved_papers", "watch_venues", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
