#!/usr/bin/env python3
"""Verify The Weather Network--6 (vacation December averages, two warmest)."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_vacation_hub", r"/en/vacation$")
    # the two warmest international December averages: Santo Domingo 29°C, Cancún 27°C
    check_visited_path(judge, traj, "visited_santo_domingo", r"/en/city/do/ozama/santo-domingo/monthly")
    check_visited_path(judge, traj, "visited_cancun", r"/en/city/mx/quintana-roo/cancun/monthly")
    check_answer_phrase(judge, answer, "answer_warmer_santo_domingo", "santo domingo")
    check_answer_number(judge, answer, "answer_dec_high", "29", label="December avg high °C")
    # the runner-up (Cancún 27°C) must appear for the comparison to be real
    check_answer_phrase(judge, answer, "answer_runnerup_cancun", "canc")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
