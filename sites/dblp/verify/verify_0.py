#!/usr/bin/env python3
"""Deterministic verifier for dblp--0.

Ground truth below is HARDCODED, frozen from the reviewer's independent
Playwright walk of this task on the review container wh-dblp-review (image
webharbor:dblp-review built from orch/review/dblp @ 8cdd14e1; seed md5
e42b5b2926de4c0ea989be80fce3ac04). Never read from tasks.jsonl.
Usage: python3 verify_0.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--0"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_combined_gnn", r"/search\?q=graph\+neural\+network")
    check_visited_path(judge, traj, "nav_publ_kind", r"/search/publ\?q=graph\+neural\+network")
    check_visited_path(judge, traj, "nav_year_facet", r"year=2026")
    check_visited_path(judge, traj, "nav_page2", r"f=30")
    check_visited_path(judge, traj, "nav_record", r"/rec/journals/pvldb/ChenTWY26")
    check_visited_path(judge, traj, "nav_venue", r"/db/journals/pvldb/index\.html")
    check_visited_path(judge, traj, "nav_edition", r"/db/journals/pvldb/pvldb19")
    check_visited_path(judge, traj, "nav_exact_rerun", r"/search\?q=graph\%24|/search/publ\?q=graph\%24|q=graph\$")
    check_visited_path(judge, traj, "nav_first_author", r"/pid/392/5344")
    check_visited_path(judge, traj, "nav_pub_venue", r"/db/conf/acl/index\.html")
    check_visited_path(judge, traj, "nav_pub_venue_edition", r"/db/conf/acl/acl2026-1")
    check_answer_number(judge, answer, "gnn_count", 287)
    check_answer_number(judge, answer, "year", 2026)
    check_answer_number(judge, answer, "year_count", 58)
    check_answer_phrase(judge, answer, "year_first_title", "From Nodes to Narratives: Explaining Graph Neural Networks with LLMs and Graph Context.")
    check_answer_number(judge, answer, "exact_count", 1558)
    check_answer_phrase(judge, answer, "page2_first_title", "ThunderGNN: Unlocking Tensor Cores for Graph Neural Networks.")
    check_answer_phrase(judge, answer, "page2_first_venue", "Proc. VLDB Endow.")
    check_answer_phrase(judge, answer, "record_type", "Journal Articles")
    check_answer_phrase(judge, answer, "record_mdate", "2026-09-27")
    check_answer_phrase(judge, answer, "bibtex_entry_type", "article")
    check_answer_number_near(judge, answer, "venue_records", 1384, "Proceedings of the VLDB Endowment")
    check_answer_phrase(judge, answer, "edition_title", "Proceedings of the VLDB Endowment, Volume 19")
    check_answer_phrase(judge, answer, "edition_first_title", "SalesforceDB: A Cloud-native Multi-tenant OLTP Database.")
    check_answer_number(judge, answer, "author_pubs", 2)
    check_answer_number(judge, answer, "author_busiest_year", 2026)
    check_answer_phrase(judge, answer, "author_newest_pub_title", "FourCorners: Grounded Thai Legal Research over a Temporal Knowledge Graph.")
    check_answer_number_near(judge, answer, "pub_venue_records", 4628, "Annual Meeting of the Association")
    check_answer_number(judge, answer, "pub_venue_edition_records", 2223)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
