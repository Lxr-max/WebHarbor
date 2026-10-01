#!/usr/bin/env python3
"""Verify Thumbtack--6.

Log in with the demo account (email: david.k@test.com, password: TestPass123!). My kitchen faucet has been dripping for a week. Find a plumber who is background checked and accepts Venmo, save them to my saved pros, and message them to confirm they can handle the leak urgently. Then request a plumbing-repair quote within a week describing the leaky faucet, and tell me the lowest quote and how it compares to the cost guide's typical range for plumbers.
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

TASK_ID = "Thumbtack--6"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
PLUMBER = "Velichkoremodels"
PLUMBER_PRO_ID = 6
URGENT_REPLY = "same-day or next-day"
LOWEST_QUOTE = 51
GUIDE_RANGE = "$50 - $200"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "plumbers category sorted", r"/k/affordable-plumbing-services/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "plumber profile", r"/wa/everett/affordable-plumbing-services/velichkoremodels-llc-emergency-restoration-247/service/550902459815264257")
    check_visited_path(judge, traj, "urgent message flow", r"/message/550902459815264257|/account/messages/2")
    check_visited_path(judge, traj, "pipe-repair wizard", r"/projects/new\?category=affordable-plumbing-services")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_visited_path(judge, traj, "plumbers cost guide", r"/p/plumbers-cost")
    check_answer_phrase(judge, answer, "plumber name", PLUMBER)
    check_answer_any(judge, answer, "background checked", ["background checked"])
    check_answer_any(judge, answer, "venmo", ["venmo"])
    check_answer_phrase(judge, answer, "urgent reply", URGENT_REPLY)
    check_answer_number(judge, answer, "lowest quote", LOWEST_QUOTE,
                        ["quote", "lowest", "cheapest"])
    check_answer_phrase(judge, answer, "guide range", GUIDE_RANGE)
    check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages",
                               "projects", "project_matches"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(14, 4, PLUMBER_PRO_ID, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 4, PLUMBER_PRO_ID, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None)])
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 4, 2, "98033", None, "Within a week", None, "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 6, 1, 189, None, None, 0),
                       (27, 6, 3, 1, 135, None, None, 0),
                       (28, 6, 1, 1, 51, None, None, 0),
                       (29, 6, 5, 1, 184, None, None, 0),
                       (30, 6, 2, 1, 169, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
