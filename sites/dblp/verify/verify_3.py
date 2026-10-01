#!/usr/bin/env python3
"""Deterministic verifier for dblp--3.

Ground truth below is HARDCODED, re-frozen from the r2-fix honest Playwright
walk of the rewritten task text on the fix container wh-dblp-fix (image
webharbor:dblp-fix built from orch/contribute/dblp with the review fixes),
then re-anchored in r3 to exactly the values the task text asks the agent
to report (the honest-minimal answer set; the reviewer's independent
Round-A facts confirm every anchored value). Seed identity is the frozen
logical contract — table counts + schema sha256 + rows sha256 pinned by
check_seed_contract; the raw seed file md5 is informational only and not
file-level deterministic across rebuilds. Never read from tasks.jsonl.
Usage: python3 verify_3.py --run_dir DIR [--initial_db P] [--after_db P]
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

TASK_ID = "dblp--3"


def run_checks(judge, traj, initial, after):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_seed_contract(judge, initial)
    answer = final_answer(traj)
    check_visited_path(judge, traj, "nav_browse", r"/db/conf/")
    check_visited_path(judge, traj, "nav_venue", r"/db/conf/nips/index\.html")
    check_visited_path(judge, traj, "nav_edition", r"/db/conf/nips/neurips2025")
    check_visited_path(judge, traj, "nav_first_paper", r"/rec/conf/nips/AamandCDMNSX25")
    check_visited_path(judge, traj, "nav_author", r"/pid/205/2416")
    check_visited_path(judge, traj, "nav_coauthor", r"/pid/254/0805")
    check_visited_path(judge, traj, "nav_co_venue", r"/db/conf/iclr/index\.html")
    check_visited_path(judge, traj, "nav_co_edition", r"/db/conf/iclr/iclr2025")
    check_visited_path(judge, traj, "nav_att_search", r"q=attention\+venue%3Aconf%2Fnips|q=attention\+venue:conf/nips")
    check_visited_path(judge, traj, "nav_att_kind", r"/search/publ\?q=attention\+venue")
    check_visited_path(judge, traj, "nav_att_page2", r"f=30")
    check_visited_path(judge, traj, "nav_att_exact", r"/search/publ\?q=attention\$|q=attention%24")
    check_answer_number(judge, answer, "conference_venues", 12)
    check_answer_number(judge, answer, "nips_records", 5823)
    check_answer_phrase(judge, answer, "top_frequent_author", "Dacheng Tao")
    check_answer_number(judge, answer, "top_frequent_count", 23)
    check_answer_phrase(judge, answer, "ed_title", "39th NeurIPS 2025: San Diago, CA, USA / Mexico City, Mexico")
    check_answer_number(judge, answer, "ed_records", 5823)
    check_answer_phrase(judge, answer, "first_paper_title", "Differentially Private Gomory-Hu Trees.")
    check_answer_count_at_least(judge, answer, "first_paper_authors", ["Anders Aamand", "Justin Y. Chen", "Mina Dalirrooyfard", "Slobodan Mitrovic", "Yuriy Nevmyvaka", "Sandeep Silwal", "Yinzhan Xu"], 5)
    check_answer_phrase(judge, answer, "first_paper_venue", "NeurIPS")
    check_answer_phrase(judge, answer, "bibtex_key", "DBLP:conf/nips/AamandCDMNSX25")
    check_answer_number(judge, answer, "author_pubs", 6)
    check_answer_phrase(judge, answer, "top_coauthor", "Justin Y. Chen")
    check_answer_number(judge, answer, "top_coauthor_joint", 4)
    check_answer_phrase(judge, answer, "co_newest_title", "Learning-Augmented Frequent Directions.")
    check_answer_number_near(judge, answer, "co_venue_records", 3704, "co_venue_records")
    check_answer_number_near(judge, answer, "co_venue_ed_records", 3704, "co_venue_ed_records")
    check_answer_number(judge, answer, "att_count", 117)
    check_answer_phrase(judge, answer, "att_first_title", "Linear Attention for Efficient Bidirectional Sequence Modeling.")
    check_answer_phrase(judge, answer, "att_page2_first_title", "Less is More: an Attention-free Sequence Prediction Modeling for Offline Embodied Learning.")
    check_answer_number(judge, answer, "att_exact_count", 332)
    check_read_only(judge, initial, after)
    check_step_action(judge, traj, "bibtex_download", "download")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
