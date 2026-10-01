#!/usr/bin/env python3
"""Deterministic verifier for dblp--5.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_5.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--5"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=transactions")
    check_visited_path(judge, traj, "nav_tifs", r"/db/journals/tifs/index\.html")
    check_visited_path(judge, traj, "nav_tmlr", r"/db/journals/tmlr/index\.html")
    check_visited_path(judge, traj, "nav_tods", r"/db/journals/tods/index\.html")
    check_visited_path(judge, traj, "nav_tods_vol", r"/db/journals/tods/tods51")
    check_visited_path(judge, traj, "nav_tods_rec", r"/rec/journals/tods/AlizadCMP26")
    check_visited_path(judge, traj, "nav_tods_author", r"/pid/423/8137")
    check_visited_path(judge, traj, "nav_tods_coauthor", r"/pid/89/5672")
    check_visited_path(judge, traj, "nav_tois", r"/db/journals/tois/index\.html")
    check_visited_path(judge, traj, "nav_tois_vol", r"/db/journals/tois/tois44")
    check_visited_path(judge, traj, "nav_tois_rec", r"/rec/journals/tois/")
    check_visited_path(judge, traj, "nav_tois_author", r"/pid/33/11411")
    check_visited_path(judge, traj, "nav_tois_co_venue", r"/db/journals/tois/index\.html")
    check_answer_number(judge, answer, "venue_matches", 4)
    check_answer_count_at_least(judge, answer, "venue_names", ["ACM Transactions on Database Systems (TODS)", "ACM Transactions on Information Systems (TOIS)", "IEEE Transactions on Information Forensics and Security", "Transactions on Machine Learning Research (TMLR)"], 4)
    check_answer_number(judge, answer, "tifs_records", 2227)
    check_answer_number(judge, answer, "tmlr_records", 2747)
    check_answer_phrase(judge, answer, "tods_iso", "ACM Trans. Database Syst.")
    check_answer_number(judge, answer, "tods_volumes", 5)
    check_answer_number_near(judge, answer, "tods_records", 84, "tods_records")
    check_answer_phrase(judge, answer, "tods_vol_title", "ACM Transactions on Database Systems, Volume 51")
    check_answer_number(judge, answer, "tods_vol_records", 24)
    check_answer_phrase(judge, answer, "tods_first_title", "Semi-Oblivious Chase Termination for Linear Existential Rules and Beyond: An Experimental Analysis.")
    check_answer_phrase(judge, answer, "tods_first_pages", "16:1-16:48")
    check_answer_number(judge, answer, "tods_author_pubs", 1)
    check_answer_phrase(judge, answer, "tods_coauthor", "Andreas Pieris")
    check_answer_number(judge, answer, "tods_coauthor_joint", 1)
    check_answer_number(judge, answer, "tods_co_pubs", 6)
    check_answer_number_near(judge, answer, "tois_records", 693, "tois_records")
    check_answer_number(judge, answer, "tois_volumes", 5)
    check_answer_phrase(judge, answer, "tois_vol_title", "ACM Transactions on Information Systems, Volume 44")
    check_answer_phrase(judge, answer, "tois_first_title", "Music Listening, Mental Health, and Stress: A Computational Framework for Personalized Analysis and Recommendation.")
    check_answer_phrase(judge, answer, "tois_ee_doi", "10.1145/3797892")
    check_answer_number(judge, answer, "tois_author_pubs", 1)
    check_answer_phrase(judge, answer, "tois_coauthor", "Amira Ghenai")
    check_answer_number(judge, answer, "tois_coauthor_joint", 1)
    check_answer_phrase(judge, answer, "tois_co_newest_title", "Music Listening, Mental Health, and Stress: A Computational Framework for Personalized Analysis and Recommendation.")
    check_answer_number(judge, answer, "tois_co_venue_records", 693)
    check_read_only(judge, initial, after)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
