#!/usr/bin/env python3
"""Deterministic verifier for dblp--6.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_6.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--6"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=query\+optimization")
    check_visited_path(judge, traj, "nav_kind", r"/search/publ\?q=query\+optimization")
    check_visited_path(judge, traj, "nav_oldest_year", r"year=2020")
    check_visited_path(judge, traj, "nav_article_type", r"type=article")
    check_visited_path(judge, traj, "nav_record", r"/rec/conf/sigmod/DingCN20")
    check_visited_path(judge, traj, "nav_author", r"/pid/163/0574")
    check_visited_path(judge, traj, "nav_coauthor", r"/pid/256/1745")
    check_visited_path(judge, traj, "nav_co_newest_pub", r"/rec/journals/pacmmod/LiYLZCM26")
    check_visited_path(judge, traj, "nav_co_venue", r"/db/journals/pacmmod/index\.html")
    check_visited_path(judge, traj, "nav_co_edition", r"/db/journals/pacmmod/pacmmod4")
    check_answer_number(judge, answer, "count", 49)
    check_answer_number(judge, answer, "oldest_year", 2020)
    check_answer_number(judge, answer, "year_count", 1)
    check_answer_phrase(judge, answer, "year_first_title", "Bitvector-aware Query Optimization for Decision Support Queries.")
    check_answer_number(judge, answer, "type_count", 42)
    check_answer_phrase(judge, answer, "record_ee_doi", "10.1145/3318464.3389769")
    check_answer_phrase(judge, answer, "record_pages", "2011-2026")
    check_answer_phrase(judge, answer, "record_mdate", "2025-01-19")
    check_answer_phrase(judge, answer, "bibtex_key", "DBLP:conf/sigmod/DingCN20")
    check_answer_phrase(judge, answer, "entry_type", "inproceedings")
    check_answer_phrase(judge, answer, "venue_field", "SIGMOD Conference")
    check_answer_number(judge, answer, "author_pubs", 7)
    check_answer_number(judge, answer, "author_busiest_year", 2025)
    check_answer_number(judge, answer, "coauthor_index_size", 45)
    check_answer_phrase(judge, answer, "top_coauthor", "Baotong Lu")
    check_answer_number(judge, answer, "top_coauthor_joint", 2)
    check_answer_phrase(judge, answer, "co_newest_title", "Corrigendum: Attribute Filtering in Approximate Nearest Neighbor Search: An In-depth Experimental Study: [Experiments & Analysis].")
    check_answer_phrase(judge, answer, "co_newest_venue", "Proc. ACM Manag. Data")
    check_answer_number_near(judge, answer, "co_venue_records", 1160, "Proc. ACM Manag. Data")
    check_answer_number(judge, answer, "co_venue_ed_records", 257)
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
