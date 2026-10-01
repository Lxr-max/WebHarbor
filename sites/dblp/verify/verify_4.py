#!/usr/bin/env python3
"""Deterministic verifier for dblp--4.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes),
then re-anchored in r3 to exactly the values the task text asks the agent
to report (the honest-minimal answer set; the reviewer's independent
Round-A facts confirm every anchored value). Seed identity is the frozen
logical contract — table counts + schema sha256 + rows sha256 pinned by
check_seed_contract; the raw seed file md5 is informational only and not
file-level deterministic across rebuilds. Never read from tasks.jsonl.
Usage: python3 verify_4.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--4"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_browse", r"/db/journals/")
    check_visited_path(judge, traj, "nav_venue", r"/db/journals/pvldb/index\.html")
    check_visited_path(judge, traj, "nav_volume", r"/db/journals/pvldb/pvldb19")
    check_visited_path(judge, traj, "nav_first_rec", r"/rec/journals/pvldb/Agrawal")
    check_visited_path(judge, traj, "nav_second_rec", r"/rec/journals/pvldb/AkidauFLM26")
    check_visited_path(judge, traj, "nav_author", r"/pid/135/4692")
    check_visited_path(judge, traj, "nav_coauthor", r"/pid/86/5332")
    check_visited_path(judge, traj, "nav_vldb_search", r"/search\?q=vldb")
    check_visited_path(judge, traj, "nav_vldbj", r"/db/journals/vldb/index\.html")
    check_answer_number(judge, answer, "journal_venues", 9)
    check_answer_number(judge, answer, "pvldb_volumes", 3)
    check_answer_phrase(judge, answer, "pvldb_top_author", "Guoliang Li 0001")
    check_answer_number(judge, answer, "pvldb_top_count", 33)
    check_answer_phrase(judge, answer, "vol_title", "Proceedings of the VLDB Endowment, Volume 19")
    check_answer_number(judge, answer, "vol_records", 457)
    check_answer_phrase(judge, answer, "first_title", "SalesforceDB: A Cloud-native Multi-tenant OLTP Database.")
    check_answer_phrase(judge, answer, "first_pages", "4426-4439")
    check_answer_phrase(judge, answer, "first_mdate", "2026-09-27")
    check_answer_phrase(judge, answer, "bibtex_entry_type", "article")
    check_answer_phrase(judge, answer, "bibtex_journal_field", "Proc. VLDB Endow.")
    check_answer_phrase(judge, answer, "second_title", "The Dataflow Model Revisited.")
    check_answer_number(judge, answer, "second_author_count", 4)
    check_answer_number(judge, answer, "author_pubs", 3)
    check_answer_number(judge, answer, "author_busiest_year", 2026)
    check_answer_phrase(judge, answer, "author_top_coauthor", "Daniel Mills")
    check_answer_number(judge, answer, "author_top_joint", 2)
    check_answer_phrase(judge, answer, "co_newest_title", "The Dataflow Model Revisited.")
    check_answer_number_near(judge, answer, "co_venue_records", 1384, "VLDB Endowment")
    check_answer_number(judge, answer, "co_venue_ed_records", 457)
    check_answer_phrase(judge, answer, "co_ed_first_title", "SalesforceDB: A Cloud-native Multi-tenant OLTP Database.")
    check_answer_number(judge, answer, "co_first_author_pubs", 1)
    check_answer_number(judge, answer, "vldb_matches", 2)
    check_answer_number_near(judge, answer, "vldbj_records", 322, "VLDB Journal")
    check_answer_number(judge, answer, "vldbj_volumes", 5)
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
