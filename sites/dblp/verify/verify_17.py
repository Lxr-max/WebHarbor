#!/usr/bin/env python3
"""Deterministic verifier for dblp--17.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes),
then re-anchored in r3 to exactly the values the task text asks the agent
to report (the honest-minimal answer set; the reviewer's independent
Round-A facts confirm every anchored value). Seed identity is the frozen
logical contract — table counts + schema sha256 + rows sha256 pinned by
check_seed_contract; the raw seed file md5 is informational only and not
file-level deterministic across rebuilds. Never read from tasks.jsonl.
Usage: python3 verify_17.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--17"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_search1", r"/search\?q=transformer\+year%3A2025|q=transformer\+year:2025")
    check_visited_path(judge, traj, "nav_author1", r"/pid/137/6768-3")
    check_visited_path(judge, traj, "nav_venue1", r"/db/conf/acl/index\.html")
    check_visited_path(judge, traj, "nav_edition1", r"/db/conf/acl/acl2026-1")
    check_visited_path(judge, traj, "nav_rec_author1", r"/pid/381/4282")
    check_visited_path(judge, traj, "nav_search2", r"/search\?q=attention\+year%3A2025|q=attention\+year:2025")
    check_visited_path(judge, traj, "nav_record2", r"/rec/conf/acl/AdigaNC25")
    check_visited_path(judge, traj, "nav_author2", r"/pid/372/0916")
    check_visited_path(judge, traj, "nav_coauthor2", r"/pid/117/4927")
    check_answer_number(judge, answer, "count", 536)
    check_answer_number(judge, answer, "author_pubs", 5)
    check_answer_number(judge, answer, "author_busiest_year", 2025)
    check_answer_phrase(judge, answer, "author_newest_title", "SAD: A Large-Scale Strategic Argumentative Dialogue Dataset.")
    check_answer_phrase(judge, answer, "author_newest_venue", "ACL (1)")
    check_answer_number_near(judge, answer, "venue_records", 4628, "venue_records")
    check_answer_phrase(judge, answer, "ed_first_title", "One Tokenizer To Rule Them All: Emergent Language Plasticity via Multilingual Tokenizers.")
    check_answer_number(judge, answer, "rec_author_pubs", 1)
    check_answer_phrase(judge, answer, "rec_top_coauthor", "Acyr Locatelli")
    check_answer_number(judge, answer, "rec_top_joint", 1)
    check_answer_number(judge, answer, "att_count", 306)
    check_answer_phrase(judge, answer, "att_first_title", "Attention Speaks Volumes: Localizing and Mitigating Bias in Language Models.")
    check_answer_phrase(judge, answer, "att_record_type", "Conference and Workshop Papers")
    check_answer_phrase(judge, answer, "att_record_mdate", "2026-06-10")
    check_answer_phrase(judge, answer, "bibtex_entry_type", "inproceedings")
    check_answer_number(judge, answer, "att_author_pubs", 1)
    check_answer_phrase(judge, answer, "att_top_coauthor", "Besmira Nushi")
    check_answer_number(judge, answer, "att_top_joint", 1)
    check_answer_phrase(judge, answer, "att_co_newest_title", "Attention Speaks Volumes: Localizing and Mitigating Bias in Language Models.")
    check_answer_phrase(judge, answer, "att_co_newest_venue", "ACL (1)")
    check_answer_number_near(judge, answer, "att_co_venue_records", 4628, "ACL")
    check_answer_number(judge, answer, "att_co_venue_ed_records", 2223)
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
