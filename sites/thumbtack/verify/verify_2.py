#!/usr/bin/env python3
"""Verify Thumbtack--2.

Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I'm planning a wedding on a tight budget. Using Thumbtack's cost guides, compare the national average cost of hiring a wedding DJ with a wedding photographer's, and tell me which service is more expensive and by roughly how much. Then find the highest-rated DJ based in Everett, message them to confirm they're available for an October wedding date, and request an estimate from them describing your four-hour wedding reception.
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

TASK_ID = "Thumbtack--2"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
DJ_AVG = 550
PHOTO_AVG = 150
EVERETT_DJ = "Cessionnation"
EVERETT_DJ_PK = 376863969460043777
DJ_REPLY = "love to be part of it"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "wedding DJ cost guide", r"/p/wedding-djs-cost")
    check_visited_path(judge, traj, "photographer cost guide", r"/p/wedding-photographer-prices")
    check_visited_path(judge, traj, "DJs category sorted", r"/k/djs/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "Everett DJ profile", r"/wa/everett/djs/cessionnation/service/376863969460043777")
    check_visited_path(judge, traj, "DJ message flow", r"/message/376863969460043777|/account/messages/2")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=djs")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_answer_number(judge, answer, "DJ national average", DJ_AVG, "dj")
    check_answer_number(judge, answer, "photographer national average", PHOTO_AVG,
                        "photographer")
    check_answer_phrase(judge, answer, "DJ more expensive", "dj")
    check_answer_phrase(judge, answer, "Everett DJ", EVERETT_DJ)
    check_answer_phrase(judge, answer, "DJ reply", DJ_REPLY)
    check_answer_phrase(judge, answer, "four-hour reception", "four-hour")
    check_answer_any(judge, answer, "estimate requested",
                     ["estimate", "quote", "request"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 19, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 3, 16, "98004", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 23, 1, 527, None, None, 0),
                       (27, 6, 19, 1, 567, None, None, 0),
                       (28, 6, 20, 0, None, None, None, 0),
                       (29, 6, 26, 1, 586, None, None, 0),
                       (30, 6, 22, 1, 520, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
