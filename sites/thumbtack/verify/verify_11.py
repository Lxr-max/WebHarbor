#!/usr/bin/env python3
"""Verify Thumbtack--11.

Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I'm budgeting my daughter's quinceañera. Using the cost guides, compare what a makeup artist charges with what a DJ charges, and tell me which is more expensive. Then find the highest-rated Top Pro makeup artist based in Redmond, message them asking whether they're available for an October event, and request an estimate from them describing the quinceañera makeup for my daughter.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_number,
                        check_answer_phrase, check_input_action,
                        check_new_user, check_only_tables_changed,
                        check_read_only, check_row_updated,
                        check_table_added, check_table_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Thumbtack--11"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
DJ_AVG = 550
MAKEUP_AVG = 167
MAKEUP_RANGE = "$156 - $178"
TARGET_PRO = "Mel Mua"
TARGET_PRO_PK = 549098172844007430
MEL_REPLY = "love to do your makeup"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "makeup artist cost guide", r"/p/makeup-artist-prices")
    check_visited_path(judge, traj, "wedding DJ cost guide", r"/p/wedding-djs-cost")
    check_visited_path(judge, traj, "makeup artists category sorted", r"/k/makeup-artists/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "target pro profile", r"/wa/redmond/makeup-artists/mel-mua/service/549098172844007430")
    check_visited_path(judge, traj, "October message flow", r"/message/549098172844007430|/account/messages/2")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=makeup-artists")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_answer_number(judge, answer, "DJ average", DJ_AVG, "dj")
    check_answer_number(judge, answer, "makeup artist average", MAKEUP_AVG,
                        "makeup")
    check_answer_phrase(judge, answer, "makeup guide range", MAKEUP_RANGE)
    check_answer_phrase(judge, answer, "target pro", TARGET_PRO)
    check_answer_any(judge, answer, "Top Pro status", ["top pro"])
    check_answer_phrase(judge, answer, "Mel reply", MEL_REPLY)
    check_answer_phrase(judge, answer, "quinceanera", "quincea")
    check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 130, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 3, 12, "98004", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 129, 1, 159, None, None, 0),
                       (27, 6, 130, 1, 162, None, None, 0),
                       (28, 6, 128, 1, 156, None, None, 0),
                       (29, 6, 131, 1, 158, None, None, 0),
                       (30, 6, 127, 1, 177, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
