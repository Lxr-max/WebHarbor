#!/usr/bin/env python3
"""Verify The Weather Network--1 (Banff Sunshine: current + 14-day snow chain
+ weekend outlook).

r2 re-sync: the task is re-anchored to Banff Sunshine (no longer free-choice)
and deepened to a cross-page fact chain. Frozen ground truth (seed rows for
ca/alberta/banff-sunshine): current 3°C/Clear; first fresh snow Sat Sep 26
(<1 cm), daytime high 4°C; coldest overnight low -6°C (unique); warmest day
Mon Oct 5 at 12°C (unique); weekend Sat 4°/60% light snow, Sun 6°/10% mainly
sunny.
"""
from verify_lib import (check_answer_any, check_answer_number, check_answer_signed_number,
                        check_read_only, check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--1"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_banff_sunshine",
                       r"/en/ski/ca/alberta/banff-sunshine/(current|14-days)")
    check_visited_path(judge, traj, "visited_banff_14days",
                       r"/en/ski/ca/alberta/banff-sunshine/14-days")
    check_visited_path(judge, traj, "visited_banff_weekend",
                       r"/en/ski/ca/alberta/banff-sunshine/weekend")
    # current conditions up there right now
    check_answer_number(judge, answer, "answer_current_temp", "3", label="current temperature")
    check_answer_any(judge, answer, "answer_current_sky", ["clear", "partly cloudy"],
                     label="current sky condition")
    # first fresh-snow date + amount + that day's high
    check_answer_any(judge, answer, "answer_first_snow_date",
                     ["september 26", "sep 26", "26th", "saturday, september 26", "this saturday"],
                     label="first fresh-snow date")
    check_answer_any(judge, answer, "answer_snow_amount",
                     ["<1", "less than 1", "under 1", "trace"],
                     label="approx snow amount")
    check_answer_number(judge, answer, "answer_first_snow_high", "4",
                        label="daytime high on the first-snow date")
    # coldest overnight low in the window
    check_answer_signed_number(judge, answer, "answer_coldest_low", "-6",
                               label="coldest overnight low")
    # warmest day of the two weeks
    check_answer_any(judge, answer, "answer_warmest_day",
                     ["october 5", "oct 5", "5th", "monday, october 5"],
                     label="warmest day of the 14")
    check_answer_number(judge, answer, "answer_warmest_high", "12",
                        label="warmest day high")
    # weekend outlook
    check_answer_any(judge, answer, "answer_saturday_outlook",
                     ["light snow", "flurries", "snow"],
                     label="Saturday outlook")
    check_answer_number(judge, answer, "answer_saturday_pop", "60", label="Saturday PoP")
    check_answer_number(judge, answer, "answer_sunday_high", "6", label="Sunday high")
    check_answer_number(judge, answer, "answer_sunday_pop", "10", label="Sunday PoP")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
