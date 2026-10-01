#!/usr/bin/env python3
"""Deterministic verifier for dblp--1.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes),
then re-anchored in r3 to exactly the values the task text asks the agent
to report (the honest-minimal answer set; the reviewer's independent
Round-A facts confirm every anchored value). Seed identity is the frozen
logical contract — table counts + schema sha256 + rows sha256 pinned by
check_seed_contract; the raw seed file md5 is informational only and not
file-level deterministic across rebuilds. Never read from tasks.jsonl.
Usage: python3 verify_1.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--1"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=jiawei\+han")
    check_visited_path(judge, traj, "nav_prof", r"/pid/h/JiaweiHan")
    check_visited_path(judge, traj, "nav_homonym", r"/pid/255/5815")
    check_visited_path(judge, traj, "nav_top_coauthor", r"/pid/235/8066")
    check_visited_path(judge, traj, "nav_author_kind", r"/search/author\?q=jiawei\$|q=jiawei%24")
    check_visited_path(judge, traj, "nav_newest_pub", r"/rec/conf/kdd/JiangSKH26")
    check_visited_path(judge, traj, "nav_venue", r"/db/conf/kdd/index\.html")
    check_visited_path(judge, traj, "nav_edition", r"/db/conf/kdd/kdd2026-1")
    check_visited_path(judge, traj, "nav_first_author", r"/pid/351/5943")
    check_answer_number(judge, answer, "profile_matches", 2)
    check_answer_phrase(judge, answer, "prof_name", "Jiawei Han 0001")
    check_answer_phrase(judge, answer, "prof_affiliation", "University of Illinois at Urbana-Champaign, Department of Computer Science, IL, USA")
    check_answer_phrase(judge, answer, "prof_award", "W. Wallace McDowell Award")
    check_answer_number(judge, answer, "prof_busiest_year", 2025)
    check_answer_number(judge, answer, "homonym_pubs", 2)
    check_answer_phrase(judge, answer, "homonym_top_coauthor", "Matteo Poggi")
    check_answer_phrase(judge, answer, "top_coauthor", "Bowen Jin")
    check_answer_number(judge, answer, "top_coauthor_joint", 6)
    check_answer_phrase(judge, answer, "co_top_coauthor", "Jiawei Han 0001")
    check_answer_number(judge, answer, "co_top_joint", 6)
    check_answer_number(judge, answer, "jiawei_exact_matches", 88)
    check_answer_phrase(judge, answer, "newest_title", "Structure Shapes the Future of DataxLLM Systems: Retrieval, Structuring, and Reasoning.")
    check_answer_phrase(judge, answer, "newest_venue", "KDD (2)")
    check_answer_number_near(judge, answer, "venue_records", 2319, "KDD")
    check_answer_number(judge, answer, "venue_busiest_year", 2026)
    check_answer_number(judge, answer, "ed_records", 256)
    check_answer_phrase(judge, answer, "ed_first_title", "VaLUH: Fast Algorithms for the Configuration Model of Vertex-Labeled Undirected Hypergraphs.")
    check_answer_number(judge, answer, "first_author_pubs", 1)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
