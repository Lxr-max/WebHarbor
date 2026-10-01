#!/usr/bin/env python3
"""Verify Thumbtack--16.

Log in with the demo account (email: david.k@test.com, password: TestPass123!). I want to get in shape this fall. Using the cost guide, tell me the typical price range for personal training sessions. Then find the highest-rated personal trainer based in Bellevue, message them to confirm they have twice-a-week slots, and request a quote from them describing twice-a-week strength sessions.
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

TASK_ID = "Thumbtack--16"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
GUIDE_RANGE = "$40 - $100"
GUIDE_AVG = 55
TARGET_PRO = "Gaskill Personal Training"
TARGET_PRO_PK = 285389944820876322
GASKILL_REPLY = "morning and evening slots"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "personal trainer cost guide", r"/p/personal-trainer-cost")
    check_visited_path(judge, traj, "trainers category sorted", r"/k/personal-trainers/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "target pro profile", r"/wa/bellevue/personal-trainers/gaskill-personal-training/service/285389944820876322")
    check_visited_path(judge, traj, "twice-a-week message flow", r"/message/285389944820876322|/account/messages/2")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=personal-trainers")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_answer_phrase(judge, answer, "guide typical range", GUIDE_RANGE)
    check_answer_number(judge, answer, "guide average", GUIDE_AVG, "average")
    check_answer_phrase(judge, answer, "target pro", TARGET_PRO)
    check_answer_phrase(judge, answer, "Gaskill reply", GASKILL_REPLY)
    check_answer_any(judge, answer, "twice-a-week quote",
                     ["twice-a-week", "twice a week"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"threads", "messages", "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 4, 136, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 4, 14, "98033", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 136, 1, 67, None, None, 0),
                       (27, 6, 138, 1, 90, None, None, 0),
                       (28, 6, 135, 1, 98, None, None, 0),
                       (29, 6, 133, 1, 60, None, None, 0),
                       (30, 6, 137, 1, 68, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
