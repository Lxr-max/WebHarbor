#!/usr/bin/env python3
"""Deterministic verifier for dblp--15.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_15.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--15"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=guoliang\+li")
    check_visited_path(judge, traj, "nav_prof", r"/pid/l/GuoliangLi")
    check_visited_path(judge, traj, "nav_top_coauthor", r"/pid/247/8418")
    check_visited_path(judge, traj, "nav_second_coauthor", r"/pid/27/104-1")
    check_visited_path(judge, traj, "nav_newest_pub", r"/rec/conf/kdd/LiWLLL26")
    check_visited_path(judge, traj, "nav_venue", r"/db/conf/kdd/index\.html")
    check_visited_path(judge, traj, "nav_edition", r"/db/conf/kdd/kdd2026-1")
    check_visited_path(judge, traj, "nav_rec_author", r"/pid/351/5943")
    check_visited_path(judge, traj, "nav_rec_coauthor", r"/pid/86/8260")
    check_visited_path(judge, traj, "nav_co_newest_pub", r"/rec/conf/kdd/AbuissaR26")
    check_answer_number(judge, answer, "author_matches", 2)
    check_answer_phrase(judge, answer, "prof_name", "Guoliang Li 0001")
    check_answer_phrase(judge, answer, "prof_affiliation", "Tsinghua University, Department of Computer Science, TNList, Beijing, China")
    check_answer_number(judge, answer, "prof_pubs", 78)
    check_answer_number(judge, answer, "prof_busiest_year", 2024)
    check_answer_number(judge, answer, "prof_busiest_count", 22)
    check_answer_phrase(judge, answer, "top_coauthor", "Xuanhe Zhou")
    check_answer_number(judge, answer, "top_coauthor_joint", 22)
    check_answer_number(judge, answer, "coauthor_index_size", 227)
    check_answer_phrase(judge, answer, "second_coauthor", "Nan Tang 0001")
    check_answer_number(judge, answer, "second_joint", 17)
    check_answer_number(judge, answer, "second_pubs", 37)
    check_answer_phrase(judge, answer, "prof_newest_title", "Automating End-to-End Hybrid Query Processing: Benchmark, Solution, and Insights.")
    check_answer_phrase(judge, answer, "prof_newest_venue", "KDD (2)")
    check_answer_phrase(judge, answer, "prof_newest_pages", "9302-9313")
    check_answer_number_near(judge, answer, "venue_records", 2319, "KDD")
    check_answer_number(judge, answer, "venue_busiest_year", 2026)
    check_answer_number(judge, answer, "ed_records", 256)
    check_answer_phrase(judge, answer, "ed_first_title", "VaLUH: Fast Algorithms for the Configuration Model of Vertex-Labeled Undirected Hypergraphs.")
    check_answer_number(judge, answer, "rec_author_pubs", 1)
    check_answer_phrase(judge, answer, "rec_top_coauthor", "Matteo Riondato")
    check_answer_phrase(judge, answer, "co_newest_title", "VaLUH: Fast Algorithms for the Configuration Model of Vertex-Labeled Undirected Hypergraphs.")
    check_answer_phrase(judge, answer, "co_newest_venue", "KDD (1)")
    check_answer_number(judge, answer, "co_venue_records", 2319)
    check_answer_number(judge, answer, "co_venue_ed_records", 256)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
