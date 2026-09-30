#!/usr/bin/env python3
"""Verify The Weather Network--19 (Banff Community High School Monday September 28).

r2 re-sync: deepened to the current-conditions check, the drop-off
temperature, and the rest-of-week verdict. Frozen ground truth: current 3°C/
Clear; Monday September 28 (Mon Sep 28) during school hours Mainly sunny, 10% PoP, no
precipitation; morning drop-off (9 AM) -1°C; daytime high 11°C; the rest of
the school week does NOT stay dry — Tue Sep 29 and Wed Sep 30 both carry
the highest rain chance (60%, 2-4 mm / 1-3 mm), so either day is a correct
"highest rain chance" answer (a tie in the frozen rows; both accepted).
"""
from verify_lib import (check_answer_any, check_answer_number, check_answer_signed_number,
                        check_read_only, check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--19"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 19)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_school_current",
                       r"/en/school/ca/alberta/banff-community-high-school/(current|$)")
    check_visited_path(judge, traj, "visited_school_hourly",
                       r"/en/school/ca/alberta/banff-community-high-school/hourly")
    check_visited_path(judge, traj, "visited_school_7days",
                       r"/en/school/ca/alberta/banff-community-high-school/7-days")
    # current conditions now
    check_answer_number(judge, answer, "answer_current_temp", "3",
                        label="current temperature at the school")
    check_answer_any(judge, answer, "answer_current_sky", ["clear", "partly cloudy"],
                     label="current sky condition")
    # Monday September 28 during school hours
    check_answer_any(judge, answer, "answer_school_hours_conditions",
                     ["mainly sunny", "sunny"], label="Monday September 28's school-hours conditions")
    check_answer_any(judge, answer, "answer_precip_verdict",
                     ["no precipitation", "no rain", "none expected", "dry", "10%"],
                     label="precipitation in Monday September 28's forecast")
    # morning drop-off temperature
    check_answer_signed_number(judge, answer, "answer_dropoff_temp", "-1",
                               label="morning drop-off temperature")
    # daytime high
    check_answer_number(judge, answer, "answer_daytime_high", "12",
                        label="Monday September 28's daytime high")
    # rest of the school week: not dry; Tue Sep 29 / Wed Sep 30 tie at 60%
    check_answer_any(judge, answer, "answer_week_not_dry",
                     ["not stay dry", "doesn't stay dry", "does not stay dry", "showers",
                      "rain later", "not dry"],
                     label="rest-of-week dry verdict")
    check_answer_any(judge, answer, "answer_highest_rain_day",
                     ["tuesday", "sep 29", "september 29", "29th",
                      "wednesday", "sep 30", "september 30", "30th"],
                     label="highest-rain-chance day (Tue/Wed tie — either accepted)")
    check_answer_number(judge, answer, "answer_highest_rain_pop", "60",
                        label="that day's rain chance")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
