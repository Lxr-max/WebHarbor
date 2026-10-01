#!/usr/bin/env python3
"""Deterministic verifier for dblp--16.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes).
Seed identity is the frozen logical contract — table counts + schema sha256
+ rows sha256 pinned by check_seed_contract; the raw seed file md5 is
informational only and not file-level deterministic across rebuilds.
Never read from tasks.jsonl.
Usage: python3 verify_16.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--16"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search", r"/search\?q=sigmod")
    check_visited_path(judge, traj, "nav_venue", r"/db/conf/sigmod/index\.html")
    check_visited_path(judge, traj, "nav_2022_edition", r"/db/conf/sigmod/sigmod2022")
    check_visited_path(judge, traj, "nav_record", r"/rec/conf/sigmod/0001022")
    check_visited_path(judge, traj, "nav_2021_edition", r"/db/conf/sigmod/sigmod2021")
    check_visited_path(judge, traj, "nav_author", r"/pid/130/8513-1")
    check_visited_path(judge, traj, "nav_coauthor", r"/pid/43/1219-1")
    check_visited_path(judge, traj, "nav_co_venue", r"/db/journals/pacmmod/index\.html")
    check_visited_path(judge, traj, "nav_year2022", r"q=sigmod\+year%3A2022|q=sigmod\+year:2022")
    check_answer_count_at_least(judge, answer, "stats", ["8,779,805", "4,205,273", "10,725", "7,159", "1,901"], 5)
    check_answer_phrase(judge, answer, "news_date", "2026-09-21")
    check_answer_phrase(judge, answer, "news_title", "Institutions as first-class citizens: introducing affiliations in dblp [Blog] [Feature Spotlight] [Blog][Feature Spotlight]")
    check_answer_phrase(judge, answer, "note_line", "International Conference on Management of Data (SIGMOD)")
    check_answer_phrase(judge, answer, "ed_title", "ACM SIGMOD Conference 2022: Philadelphia, PA, USA")
    check_answer_number(judge, answer, "ed_records", 222)
    check_answer_phrase(judge, answer, "record_title", "Conjunctive Queries with Comparisons.")
    check_answer_phrase(judge, answer, "record_pages", "108-121")
    check_answer_phrase(judge, answer, "record_ee_doi", "10.1145/3514221.3517830")
    check_answer_phrase(judge, answer, "bibtex_entry_type", "inproceedings")
    check_answer_phrase(judge, answer, "venue_link_leads_to", "ACM SIGMOD Conference (SIGMOD)")
    check_answer_phrase(judge, answer, "ed21_title", "ACM SIGMOD Conference 2021: Virtual Event, China")
    check_answer_number(judge, answer, "ed21_records", 270)
    check_answer_phrase(judge, answer, "ed_first_title", "Conjunctive Queries with Comparisons.")
    check_answer_number(judge, answer, "author_pubs", 13)
    check_answer_phrase(judge, answer, "top_coauthor", "Ke Yi 0001")
    check_answer_phrase(judge, answer, "co_newest_title", "PACMMOD, V4, N2 (PODS), May 2026 Editorial.")
    check_answer_phrase(judge, answer, "co_newest_venue", "Proc. ACM Manag. Data")
    check_answer_number_near(judge, answer, "co_venue_records", 1160, "Proc. ACM Manag. Data")
    check_answer_number(judge, answer, "year2022_count", 222)
    check_answer_phrase(judge, answer, "year2022_first_title", "Conjunctive Queries with Comparisons.")
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
