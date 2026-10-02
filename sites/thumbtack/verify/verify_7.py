#!/usr/bin/env python3
"""Verify Thumbtack--7.

Create a new Thumbtack account (name: Nina Patel, email: nina.p@test.com, password: NewHome2026!), then request quotes for assembling a large wardrobe and two bookcases in zip 98101, answering the questionnaire about the three items and the instructions you have and describing the job. Hire the cheapest pro who responded, mark the project complete, and leave them a 5-star review mentioning the smooth assembly. Tell me how many pros responded and what the cheapest quote was.
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

TASK_ID = "Thumbtack--7"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
NEW_USER = "Nina Patel"
NEW_EMAIL = "nina.p@test.com"
NEW_USERNAME = "nina.p"
N_RESPONDERS = 4
CHEAPEST_QUOTE = 107
HIRED_PRO_ID = 52
WIZARD_ANSWERS = ('[["Number of items", "3 items"], '
                  '["Instructions or make/model provided by client?", '
                  '"Yes, I have assembly instructions or make and model information"]]')



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "registration page", r"/register")
    check_visited_path(judge, traj, "furniture assembly category", r"/k/furniture-assembly/near-me")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=furniture-assembly")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "review form", r"/projects/6/review")
    check_answer_number(judge, answer, "responders", N_RESPONDERS,
                        ["respond", "pros"])
    check_answer_number(judge, answer, "cheapest quote", CHEAPEST_QUOTE,
                        ["quote", "cheapest"])
    check_answer_any(judge, answer, "smooth assembly review",
                     ["smooth assembly", "smooth"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"users", "projects", "project_matches", "reviews"})
    check_new_user(judge, initial_db, after_db, NEW_EMAIL,
                    "nina.p", NEW_USER)
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 5, 9, "98101", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 49, 1, 180, None, None, 0),
                       (27, 6, 44, 0, None, None, None, 0),
                       (28, 6, 46, 1, 131, None, None, 0),
                       (29, 6, HIRED_PRO_ID, 1, 107, None, None, 1),
                       (30, 6, 50, 1, 144, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, NEW_USER, "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
