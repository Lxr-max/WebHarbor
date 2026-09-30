#!/usr/bin/env python3
"""Verify The Weather Network--0 (weekend forecast comparison, 3 cities)."""
from verify_lib import (check_answer_any, check_answer_number, check_answer_phrase,
                        check_read_only, check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--0"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 0)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_toronto_weekend", r"/en/city/ca/ontario/toronto/weekend")
    check_visited_path(judge, traj, "visited_montreal_weekend", r"/en/city/ca/quebec/montreal/weekend")
    check_visited_path(judge, traj, "visited_halifax_weekend", r"/en/city/ca/nova-scotia/halifax/weekend")
    # warmest overall: Toronto (Sat 22 / Sun 23 vs Montréal 22/20, Halifax 17/17)
    check_answer_phrase(judge, answer, "answer_warmest_toronto", "toronto")
    # PoP for each weekend day in the winning city: Sat 20%, Sun 30%
    check_answer_number(judge, answer, "answer_sat_pop", "20", label="Saturday PoP")
    check_answer_number(judge, answer, "answer_sun_pop", "30", label="Sunday PoP")
    # the weekend highs the comparison is built on (Toronto 22 / 23)
    check_answer_number(judge, answer, "answer_high_22", "22", label="weekend high")
    check_answer_number(judge, answer, "answer_high_23", "23", label="weekend high")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
