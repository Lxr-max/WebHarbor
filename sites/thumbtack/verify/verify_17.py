#!/usr/bin/env python3
"""Verify Thumbtack--17.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I want my 75-inch TV mounted above the fireplace with the cables hidden and my sound bar connected. Request TV mounting quotes in zip 98052, answering the questionnaire to match my setup and describing the job. Hire the pro with the lowest quote, mark the project complete, and leave them a 5-star review mentioning the tidy cable work. Tell me how many pros responded and which one you hired.
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

TASK_ID = "Thumbtack--17"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
N_RESPONDERS = 4
LOWEST_QUOTE = 127
HIRED_PRO = "Mmy"
HIRED_PRO_ID = 160
WIZARD_ANSWERS = ('[["Conceal cables/wires?", "Yes, I need to conceal cables and wires"], '
                  '["Sound system", "Sound bar"], '
                  '["TV installation location", "Wall mount above fireplace"]]')



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "TV mounting category", r"/k/tv-wall-mount-install/near-me")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=tv-wall-mount-install")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "review form", r"/projects/6/review")
    check_answer_number(judge, answer, "responders", N_RESPONDERS,
                        ["respond", "pros"])
    check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,
                        ["quote", "lowest"])
    check_answer_phrase(judge, answer, "hired pro", HIRED_PRO)
    check_answer_any(judge, answer, "tidy cable review",
                     ["tidy cable", "tidy"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"projects", "project_matches", "reviews"})
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 1, 8, "98052", None, None, WIZARD_ANSWERS,
                        "completed", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 162, 1, 220, None, None, 0),
                       (27, 6, 163, 0, None, None, None, 0),
                       (28, 6, HIRED_PRO_ID, 1, 127, None, None, 1),
                       (29, 6, 161, 1, 173, None, None, 0),
                       (30, 6, 159, 1, 187, None, None, 0)])
    check_table_added(judge, initial_db, after_db, "reviews",
                      [(857, HIRED_PRO_ID, "Alice Johnson", "Sep 26, 2026", 5,
                        None, "project:6", 1, "user")])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
