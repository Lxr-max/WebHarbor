#!/usr/bin/env python3
"""Verify The Weather Network--2 (Winnipegosis + Dauphin alerts, full chain).

r2 re-sync: deepened to per-alert issue/expiry times and the end-time
comparison. Frozen ground truth: both communities sit under separate High
Water Level records for the Mossey River area, both issued Wed 3:53 PM
Sep. 23 and both expiring Wed 9:00 PM Sep. 30 (so they DO end at the same
time); the bulletin recommends being aware and exercising caution near
waterways, not crossing fast-flowing water, avoiding flooded areas and
following local authorities' directions.
"""
from verify_lib import (check_answer_any, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--2"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_alerts_index", r"/en/alerts/ca")
    check_visited_path(judge, traj, "visited_winnipegosis_alert",
                       r"/en/alerts/ca/W_CSD4617073")
    check_visited_path(judge, traj, "visited_dauphin_alert",
                       r"/en/alerts/ca/W_CSD4617048")
    # alert kind for both
    check_answer_any(judge, answer, "answer_alert_kind",
                     ["high water level", "high water"],
                     label="alert kind")
    # issued + expiry for each
    check_answer_any(judge, answer, "answer_issued",
                     ["3:53", "wed 3:53", "wednesday 3:53"],
                     label="issued time")
    check_answer_any(judge, answer, "answer_expiry",
                     ["9:00 pm", "9 pm", "wed 9:00", "wednesday 9:00", "sept. 30", "september 30"],
                     label="expiry time")
    # what the bulletin recommends
    check_answer_any(judge, answer, "answer_recommendation",
                     ["caution", "avoid flooded", "exercise caution", "do not attempt to cross",
                      "not attempt to cross", "follow directions", "local authorities"],
                     label="bulletin recommendation")
    # same alert or different ones
    check_answer_any(judge, answer, "answer_same_or_different",
                     ["different", "separate", "two alerts", "distinct"],
                     label="same-or-different verdict")
    # do the two alerts end at the same time
    check_answer_any(judge, answer, "answer_end_same_time",
                     ["same time", "both end", "end at the same", "both expire", "yes"],
                     label="end-time comparison")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
