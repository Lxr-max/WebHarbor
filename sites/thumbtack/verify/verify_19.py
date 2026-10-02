#!/usr/bin/env python3
"""Verify Thumbtack--19.

Log in with the demo account (email: bob.c@test.com, password: TestPass123!). My refrigerator stopped cooling overnight and my food is spoiling. Find the appliance repair specialist who responds fastest, request a quote describing the emergency repair for my GE refrigerator, hire the pro with the lowest quote, and leave them a 5-star review mentioning the refrigerator. Tell me the lowest quote you received.
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

TASK_ID = "Thumbtack--19"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
FASTEST_PRO = "Hotwire Hvac Refrigeration & Appliance Repair"
FASTEST_RESPONSE = "1 min"
LOWEST_QUOTE = 130
HIRED_PRO_ID = 18
WIZARD_ANSWERS = ('[["Appliance type", "Refrigerator"], '
                  '["Appliance brand", "GE"]]')



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "appliance category sorted by fastest response", r"/k/appliance-repair/near-me\?sort=fastest_response")
    check_visited_path(judge, traj, "fastest pro profile", r"/wa/woodinville/appliance-repair/hotwire-hvac-refrigeration-appliance-repair/service/500453696558571522")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=appliance-repair")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "review form", r"/projects/6/review")
    check_answer_phrase(judge, answer, "fastest pro", "Hotwire")
    check_answer_phrase(judge, answer, "fastest response", FASTEST_RESPONSE)
    check_answer_phrase(judge, answer, "GE refrigerator", "GE")
    check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,
                        ["quote", "lowest"])
    check_answer_any(judge, answer, "refrigerator review", ["refrigerator"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 6, "98101", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 11, 1, 275, None, None, 0),
                       (27, 6, 9, 1, 328, None, None, 0),
                       (28, 6, HIRED_PRO_ID, 1, 130, None, None, 1),
                       (29, 6, 17, 1, 319, None, None, 0),
                       (30, 6, 14, 1, 232, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Bob Chen", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
