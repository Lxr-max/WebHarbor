#!/usr/bin/env python3
"""Verify Thumbtack--10.

Log in with the demo account (email: bob.c@test.com, password: TestPass123!). My moving plans changed. Remove the moving companies from my saved pros, open my pending moving project, and tell me which pro quoted the lowest price — check that pro's profile for their rating and how fast they respond. Then cancel the project and start a much smaller replacement request for a studio move in zip 98101, telling me how many pros respond this time.
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

TASK_ID = "Thumbtack--10"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
MOVER_ONE = "At Moving"
MOVER_TWO = "John Frank Moving"
LOWEST_QUOTE = 199
LOWEST_PRO = "Strok Industries Moving Company"
STROK_RATING = "4.9"
STROK_RESPONSE = "within a day"
N_NEW_QUOTES = 5



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "saved list", r"/account/saved")
    check_visited_path(judge, traj, "moving project", r"/projects/3")
    check_visited_path(judge, traj, "lowest-quote pro profile", r"/wa/kent/local-movers/strok-industries-moving-company/service/537096908478578695")
    check_visited_path(judge, traj, "local movers category", r"/k/local-movers/near-me")
    check_visited_path(judge, traj, "replacement wizard", r"/projects/new\?category=local-movers")
    check_visited_path(judge, traj, "replacement project page", r"/projects/6")
    check_answer_phrase(judge, answer, "removed mover one", MOVER_ONE)
    check_answer_phrase(judge, answer, "removed mover two", MOVER_TWO)
    check_answer_phrase(judge, answer, "lowest-quote pro", LOWEST_PRO)
    check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,
                        ["quote", "lowest"])
    check_answer_phrase(judge, answer, "Strok rating", STROK_RATING)
    check_answer_phrase(judge, answer, "Strok response speed", STROK_RESPONSE)
    check_answer_any(judge, answer, "cancelled", ["cancel"])
    check_answer_number(judge, answer, "replacement quotes", N_NEW_QUOTES,
                        ["quotes", "respond", "received"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "projects", "project_matches"})
    check_table_removed(judge, initial_db, after_db, "saved_pros", 2,
                        "user_id = 2 AND pro_id IN (117, 119)")
    check_row_updated(judge, initial_db, after_db, "projects", "id = 3",
                      "status", "cancelled")
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 2, 15, "98101", None, None, None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 119, 1, 274, None, None, 0),
                       (27, 6, 117, 1, 174, None, None, 0),
                       (28, 6, 115, 1, 224, None, None, 0),
                       (29, 6, 124, 1, 233, None, None, 0),
                       (30, 6, 118, 1, 261, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
