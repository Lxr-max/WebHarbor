#!/usr/bin/env python3
"""Deterministic verifier for dblp--19.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_19.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--19"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_zhang_search", r"q=zhang")
    check_visited_path(judge, traj, "nav_zhang_kind", r"/search/author\?q=zhang")
    check_visited_path(judge, traj, "nav_zhang_page2", r"/search/author\?q=zhang\&h=30\&f=30|f=30[^ ]*q=zhang|q=zhang[^ ]*f=30")
    check_visited_path(judge, traj, "nav_page2_profile", r"/pid/142/9150")
    check_visited_path(judge, traj, "nav_top_coauthor", r"/pid/48/7536-1")
    check_visited_path(judge, traj, "nav_co_venue", r"/db/conf/iclr/index\.html")
    check_visited_path(judge, traj, "nav_min_search", r"q=min\+zhang")
    check_visited_path(judge, traj, "nav_min_kind", r"/search/author\?q=min\+zhang")
    check_visited_path(judge, traj, "nav_best_profile", r"/pid/83/5342-5")
    check_visited_path(judge, traj, "nav_min_venue", r"/db/conf/acl/index\.html")
    check_visited_path(judge, traj, "nav_min_edition", r"/db/conf/acl/acl2026-1")
    check_visited_path(judge, traj, "nav_ed_first_author", r"/pid/381/4282")
    check_answer_number(judge, answer, "zhang_matches", 3639)
    check_answer_phrase(judge, answer, "page2_first_name", "Aston Zhang")
    check_answer_number(judge, answer, "page2_first_pubs", 2)
    check_answer_number(judge, answer, "page2_first_busiest_year", 2025)
    check_answer_phrase(judge, answer, "top_coauthor", "Chenguang Zhu 0001")
    check_answer_number(judge, answer, "top_coauthor_joint", 1)
    check_answer_number(judge, answer, "co_venue_records", 3704)
    check_answer_number(judge, answer, "min_matches", 56)
    check_answer_number(judge, answer, "min_best_pubs", 68)
    check_answer_phrase(judge, answer, "min_best_name", "Min Zhang 0005")
    check_answer_phrase(judge, answer, "min_newest_title", "Dynamic Long Context Reasoning over Compressed Memory via End-to-End Reinforcement Learning.")
    check_answer_number(judge, answer, "min_venue_records", 4628)
    check_answer_number(judge, answer, "min_venue_busiest_year", 2026)
    check_answer_number(judge, answer, "min_edition_records", 2223)
    check_answer_phrase(judge, answer, "min_ed_first_title", "One Tokenizer To Rule Them All: Emergent Language Plasticity via Multilingual Tokenizers.")
    check_answer_number(judge, answer, "min_rec_author_pubs", 1)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
