#!/usr/bin/env python3
"""Deterministic verifier for dblp--7.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_7.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--7"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_or_search", r"/search\?q=graph\%7Cnetwork|q=graph\|network")
    check_visited_path(judge, traj, "nav_exact_search", r"q=network\$|q=network%24")
    check_visited_path(judge, traj, "nav_kind", r"/search/publ\?q=graph")
    check_visited_path(judge, traj, "nav_type_refine", r"type=inproceedings")
    check_visited_path(judge, traj, "nav_year_refine", r"year=2026")
    check_visited_path(judge, traj, "nav_page2", r"f=30")
    check_visited_path(judge, traj, "nav_record", r"/rec/conf/acl/KerdabadiMCWY26")
    check_visited_path(judge, traj, "nav_author", r"/pid/381/4282")
    check_visited_path(judge, traj, "nav_venue", r"/db/conf/acl/index\.html")
    check_visited_path(judge, traj, "nav_edition", r"/db/conf/acl/acl2026-1")
    check_answer_number(judge, answer, "or_count", 3724)
    check_answer_number(judge, answer, "exact_count", 557)
    check_answer_number(judge, answer, "type_count", 2333)
    check_answer_number(judge, answer, "year", 2026)
    check_answer_number(judge, answer, "year_count", 1039)
    check_answer_phrase(judge, answer, "year_first_title", "FourCorners: Grounded Thai Legal Research over a Temporal Knowledge Graph.")
    check_answer_phrase(judge, answer, "year_first_venue", "ACL (3)")
    check_answer_phrase(judge, answer, "page2_first_title", "Text-Attributed Knowledge Graph Enrichment with Large Language Models for Medical Concept Representation.")
    check_answer_phrase(judge, answer, "page2_first_venue", "ACL (1)")
    check_answer_phrase(judge, answer, "record_ee_doi", "10.18653/v1/2026.acl-long.753")
    check_answer_phrase(judge, answer, "record_mdate", "2026-08-14")
    check_answer_phrase(judge, answer, "bibtex_entry_type", "inproceedings")
    check_answer_number_near(judge, answer, "venue_editions", 12, "ACL")
    check_answer_number(judge, answer, "venue_busiest_year", 2026)
    check_answer_number(judge, answer, "ed_records", 2223)
    check_answer_phrase(judge, answer, "ed_first_title", "One Tokenizer To Rule Them All: Emergent Language Plasticity via Multilingual Tokenizers.")
    check_answer_number(judge, answer, "author_pubs", 1)
    check_answer_phrase(judge, answer, "top_coauthor", "Acyr Locatelli")
    check_answer_number(judge, answer, "top_coauthor_joint", 1)
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
