#!/usr/bin/env python3
"""Verify The Weather Network--13 (Baker Lake extremes + monthly + alert).

r2 re-sync: re-anchored to unique extremes and extended with the monthly
cross-check and the active alert. Frozen ground truth: warmest daytime high
7°C on Mon Sep 28 (unique); coldest overnight low -3°C (unique); wettest day
Sun Sep 27 with 10-15 mm (unique max); monthly averages give Sep 28 a
typical daytime high of 3°C, so the forecast is 4° warmer than average; the
active alert covering Baker Lake is a Yellow Warning - Rainfall expiring
Sun 1:15 AM (Sep 27 01:15).
"""
from verify_lib import (check_answer_any, check_answer_number, check_answer_signed_number,
                        check_read_only, check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--13"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_baker_lake_14d",
                       r"/en/city/ca/nunavut/baker-lake/14-days")
    check_visited_path(judge, traj, "visited_baker_lake_monthly",
                       r"/en/city/ca/nunavut/baker-lake/monthly")
    check_visited_path(judge, traj, "visited_baker_lake_alert",
                       r"/en/alerts/ca/W_WWCANU0006")
    # warmest daytime high + its date (unique)
    check_answer_number(judge, answer, "answer_warmest_high", "7",
                        label="warmest daytime high")
    check_answer_any(judge, answer, "answer_warmest_date",
                     ["september 28", "sep 28", "28th", "monday"],
                     label="warmest high date")
    # coldest overnight low (unique)
    check_answer_signed_number(judge, answer, "answer_coldest_low", "-3",
                               label="coldest overnight low")
    # wettest day + roughly how much rain (unique max)
    check_answer_any(judge, answer, "answer_wettest_day",
                     ["september 27", "sep 27", "27th", "sunday"],
                     label="wettest day")
    check_answer_any(judge, answer, "answer_wettest_amount",
                     ["10-15", "10 to 15", "between 10 and 15", "10–15", "10-15 mm"],
                     label="roughly how much rain on the wettest day")
    # monthly averages: typical high for the warmest date + how much warmer
    check_answer_number(judge, answer, "answer_monthly_typical_high", "3",
                        label="typical daytime high for Sep 28 (monthly averages)")
    check_answer_number(judge, answer, "answer_warmer_than_average", "4",
                        label="degrees warmer than average")
    # active alert covering Baker Lake + when it ends
    check_answer_any(judge, answer, "answer_alert_kind",
                     ["yellow warning", "rainfall warning", "warning - rainfall"],
                     label="Baker Lake alert kind")
    check_answer_any(judge, answer, "answer_alert_end",
                     ["1:15", "sun 1:15", "sunday 1:15"],
                     label="when the Baker Lake alert ends")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
