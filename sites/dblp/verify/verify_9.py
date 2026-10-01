#!/usr/bin/env python3
"""Deterministic verifier for dblp--9.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_9.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--9"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_login", r"/authn/login")
    check_visited_path(judge, traj, "nav_watchlist", r"/account/watchlist")
    check_visited_path(judge, traj, "nav_search", r"/search\?q=jiawei\+han|/search/author\?q=jiawei\+han")
    check_visited_path(judge, traj, "nav_prof", r"/pid/h/JiaweiHan")
    check_visited_path(judge, traj, "nav_nips", r"/db/conf/nips/index\.html")
    check_visited_path(judge, traj, "nav_nips_edition", r"/db/conf/nips/neurips2025")
    check_answer_count_at_least(judge, answer, "seed_authors", ["Dacheng Tao", "Li Shen 0008", "Lei Bai 0001"], 3)
    check_answer_count_at_least(judge, answer, "seed_author_counts", ["72", "50", "42"], 3)
    check_answer_count_at_least(judge, answer, "seed_venues", ["Conference on Neural Information Processing Systems (NeurIPS)", "International Conference on Machine Learning (ICML)"], 2)
    check_answer_number(judge, answer, "after_add_total", 4)
    check_answer_phrase(judge, answer, "added_author", "Jiawei Han 0001")
    check_answer_number(judge, answer, "nips_records", 5823)
    check_answer_number(judge, answer, "nips_busiest_year", 2025)
    check_answer_number(judge, answer, "nips_edition_records", 5823)
    check_answer_phrase(judge, answer, "remaining_venue", "International Conference on Machine Learning (ICML)")
    # alice (user 1): +1 Jiawei Han watch, -1 seeded author watch, -1 NeurIPS venue
    added, removed, _ = _diff(initial, after, "watch_authors")
    seed_pids = {"46/3391", "91/3680-8", "119/1223-1"}
    ok_add = len(added) == 1 and added[0][2] == "h/JiaweiHan"
    ok_rm = len(removed) == 1 and removed[0][2] in seed_pids
    if ok_add and ok_rm:
        judge.ok("watch_authors_delta", f"+{added[0][2]} -{removed[0][2]}")
    else:
        judge.fail("watch_authors_delta", f"added {added} removed {removed}")
    added, removed, _ = _diff(initial, after, "watch_venues")
    if len(removed) == 1 and removed[0][2] == 6 and not added:
        judge.ok("watch_venues_delta", "NeurIPS (venue 6) removed")
    else:
        judge.fail("watch_venues_delta", f"added {added} removed {removed}")
    added, _, _ = _diff(initial, after, "search_history")
    bad = [r for r in added if r[1] != 1 or r[2] != "jiawei han" or r[4] != 64]
    if not (1 <= len(added) <= 3) or bad:
        judge.fail("history_added", f"unexpected history rows: {added}")
    else:
        judge.ok("history_added", f"{len(added)} jiawei-han row(s)")
    check_only_tables_changed(judge, initial, after,
                              {"watch_authors", "watch_venues", "search_history"})


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
