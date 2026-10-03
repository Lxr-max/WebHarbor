#!/usr/bin/env python3
"""Verify Thumbtack--14.

Log in with the demo account (email: bob.c@test.com, password: TestPass123!). Ants have invaded my kitchen. Check the cost guide for what an exterminator typically runs, then find the exterminators who are Top Pros and request quotes for indoor ant treatment in zip 98101 within a week, describing the problem. Hire the responder with the most reviews, mark the project complete, and leave them a 5-star review mentioning the ants. Confirm on their profile that your review shows, and tell me their name, their quote, and the guide's typical range.
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

TASK_ID = "Thumbtack--14"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
GUIDE_RANGE = "$131 - $341"
HIRED_PRO = "Super Attic Solutions"
HIRED_PRO_ID = 38
HIRED_REVIEWS = 123
HIRED_QUOTE = 315



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "exterminator cost guide", r"/p/exterminators-prices")
    check_visited_path(judge, traj, "exterminators category", r"/k/exterminators/near-me")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=exterminators")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "review form", r"/projects/6/review")
    check_visited_path(judge, traj, "hired pro profile", r"/wa/kirkland/exterminators/super-attic-solutions/service/472430256251617281")
    check_answer_phrase(judge, answer, "guide typical range", GUIDE_RANGE)
    check_answer_phrase(judge, answer, "hired pro name", HIRED_PRO)
    check_answer_number(judge, answer, "hired pro reviews", HIRED_REVIEWS,
                        "review")
    check_answer_number(judge, answer, "hired quote", HIRED_QUOTE,
                        ["quote", "quoted"])
    check_answer_any(judge, answer, "ants review", ["ants", "ant"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 11, "98101", None, "Within a week", None,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 36, 1, 250, None, None, 0),
                       (27, 6, 40, 1, 170, None, None, 0),
                       (28, 6, 32, 1, 207, None, None, 0),
                       (29, 6, 41, 1, 137, None, None, 0),
                       (30, 6, HIRED_PRO_ID, 1, 315, None, None, 1)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
