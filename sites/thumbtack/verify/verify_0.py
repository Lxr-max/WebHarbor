#!/usr/bin/env python3
"""Verify Thumbtack--0.

Log in with the demo account (email: alice.j@test.com, password: TestPass123!). I'm choosing between the Seattle wedding photographers Jeshua Frees (Clearline Production), Tanner Schmidt, and Liz Ong. Compare how many Thumbtack hires each of them has, save the one with the most hires to my saved pros, and tell me how many years that pro has been in business and how many employees they have.
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

TASK_ID = "Thumbtack--0"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
JESHUA_HIRES = 69
TANNER_HIRES = 30
WINNER = "Jeshua Frees"
WINNER_YEARS = 7
WINNER_EMPLOYEES = 19
WINNER_PRO_ID = 169


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "Jeshua profile",
                       r"/wa/seattle/wedding-photographers/jeshua-frees-clearline-production/service/510542342918987781")
    check_visited_path(judge, traj, "Tanner profile",
                       r"/wa/seattle/wedding-photographers/tanner-schmidt/service/508112018197602315")
    check_answer_phrase(judge, answer, "winner name", "Jeshua")
    check_answer_number(judge, answer, "winner hires", JESHUA_HIRES, "hire")
    check_answer_number(judge, answer, "years in business", WINNER_YEARS, "year")
    check_answer_number(judge, answer, "employees", WINNER_EMPLOYEES, "employee")
    check_answer_any(judge, answer, "saved confirmation",
                     ["saved", "save"])
    check_only_tables_changed(judge, initial_db, after_db, {"saved_pros"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(None, 1, WINNER_PRO_ID, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
