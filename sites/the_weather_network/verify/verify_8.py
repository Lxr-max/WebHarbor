#!/usr/bin/env python3
"""Verify The Weather Network--8 (radar cities + Ontario comparison + alerts).

r2 re-sync: deepened with the sky conditions and the national/ON alert
counts. Frozen ground truth: 7 radar cities (Toronto ON, Montréal QC,
Vancouver BC, Victoria BC, Calgary AB, Edmonton AB, Halifax NS — ON and BC
have more than one); Ottawa 13°C/Partly cloudy vs Toronto 18°C/Clear
(Toronto warmer); 51 alerts in effect across Canada; Ontario has none (not
even listed among the region chips).
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--8"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 8)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_radar", r"/en/maps/radar")
    check_visited_path(judge, traj, "visited_ottawa", r"/en/city/ca/ontario/ottawa")
    check_visited_path(judge, traj, "visited_toronto", r"/en/city/ca/ontario/toronto")
    check_visited_path(judge, traj, "visited_alerts", r"/en/alerts/ca")
    # radar cities + provinces with more than one
    # the two Ontario radar cities: warmer + sky condition in each
    check_answer_any(judge, answer, "answer_warmer_city", ["toronto"],
                     label="warmer Ontario radar city")
    check_answer_number(judge, answer, "answer_toronto_temp", "18",
                        label="Toronto current temperature")
    check_answer_any(judge, answer, "answer_toronto_sky", ["clear"],
                     label="Toronto sky condition")
    check_answer_number(judge, answer, "answer_ottawa_temp", "13",
                        label="Ottawa current temperature")
    check_answer_any(judge, answer, "answer_ottawa_sky", ["partly cloudy"],
                     label="Ottawa sky condition")
    # national alert total + Ontario
    check_answer_any(judge, answer, "answer_ontario_alerts",
                     ["no active", "none", "no alerts", "does not have", "doesn't have",
                      "not currently", "no weather alerts"],
                     label="Ontario active-alert verdict")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
