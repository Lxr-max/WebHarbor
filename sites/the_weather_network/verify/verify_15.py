#!/usr/bin/env python3
"""Verify The Weather Network--15 (alert province statistics + Nunavut).

r2 re-sync: deepened to the national total, the Nunavut leg and expiry
times. Frozen ground truth: 51 alerts in effect across Canada; Alberta has
the most (40); the dominant kind there is Yellow Advisory - Frost and its
bulletins recommend taking preventative measures — covering up
cold-sensitive plants, especially in frost-prone areas; Nunavut has 3
active alerts, all Yellow Warning - Rainfall, expiring Sun 1:15 AM.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--15"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_alerts_index", r"/en/alerts/ca")
    check_visited_path(judge, traj, "visited_ab_filter", r"/en/alerts/ca\?region=AB")
    check_visited_path(judge, traj, "visited_ab_alert_detail", r"/en/alerts/ca/W_WWCAAB")
    check_visited_path(judge, traj, "visited_nu_filter", r"/en/alerts/ca\?region=NU")
    check_visited_path(judge, traj, "visited_nu_alert_detail", r"/en/alerts/ca/W_WWCANU")
    # national total + province with the most
    check_answer_number(judge, answer, "answer_national_total", "51",
                        label="alerts in effect across Canada")
    check_answer_any(judge, answer, "answer_most_province", ["alberta"],
                     label="province with the most alerts")
    check_answer_number(judge, answer, "answer_ab_count", "40",
                        label="Alberta alert count")
    # dominant kind + recommendation
    check_answer_any(judge, answer, "answer_dominant_kind",
                     ["yellow advisory", "frost advisory", "advisory - frost"],
                     label="dominant alert kind in Alberta")
    check_answer_any(judge, answer, "answer_recommendation",
                     ["cover up", "cover plants", "protect cold-sensitive",
                      "preventative measures", "cover up plants"],
                     label="what the bulletins recommend")
    # Nunavut leg
    check_answer_number(judge, answer, "answer_nu_count", "3",
                        label="Nunavut active alerts")
    check_answer_any(judge, answer, "answer_nu_kind",
                     ["yellow warning", "rainfall warning", "warning - rainfall"],
                     label="Nunavut alert kind")
    check_answer_any(judge, answer, "answer_nu_expiry",
                     ["1:15", "sun 1:15", "sunday 1:15"],
                     label="when the Nunavut alerts expire")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
