#!/usr/bin/env python3
"""Verify The Weather Network--7 (Toronto fence-painting rain window).

r3 incremental re-sync (onto the deepened T7 @ 2d15effd): the task now also
asks how cold it gets overnight during the rain (14°C, Mon 4-5 AM rows),
how warm Monday afternoon gets after the rain (20°C, Mon 1-3 PM rows), and
how much rain the highest-rain-chance day expects (5-10 mm).
Frozen ground truth (Toronto seed rows): current 18°C/Clear; hourly window
— rain starts Sun 11 PM (Sep 27 23:00), last showers Mon 5 AM (Sep 28
05:00), 7 rain hours, highest PoP during them 60%, dry-stretch
temperatures before the rain span 12-23°C; 7-day — the day later in the
week with the highest rain chance is Thursday, Oct. 1 (70%, 5-10 mm).

NOTE (r2 adversarial finding): the fix receipt's own walk recorded the 7-day
answer as "Tue Sep 30, 60%" — that is wrong against the frozen rows (Sep 30
is a Wednesday at 60%; the unique maximum is Thursday Oct. 1 at 70%). This
verifier encodes the frozen-data truth.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--7"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_toronto_current",
                       r"/en/city/ca/ontario/toronto/(current|$)")
    check_visited_path(judge, traj, "visited_toronto_hourly",
                       r"/en/city/ca/ontario/toronto/hourly")
    check_visited_path(judge, traj, "visited_toronto_7days",
                       r"/en/city/ca/ontario/toronto/7-days")
    # current conditions
    check_answer_number(judge, answer, "answer_current_temp", "18",
                        label="Toronto current temperature")
    check_answer_any(judge, answer, "answer_current_sky", ["clear", "partly cloudy"],
                     label="current sky condition")
    # rain start / clear, anchored to hours
    check_answer_any(judge, answer, "answer_rain_start",
                     ["11 pm", "11pm", "11 p.m", "eleven pm"],
                     label="rain start hour")
    check_answer_any(judge, answer, "answer_rain_start_day",
                     ["sunday", "sun 11", "sep 27", "september 27"],
                     label="rain start day")
    check_answer_any(judge, answer, "answer_rain_clear",
                     ["5 am", "5am", "5 a.m", "five am"],
                     label="last showers clear hour")
    check_answer_any(judge, answer, "answer_rain_clear_day",
                     ["monday", "mon 5", "sep 28", "september 28"],
                     label="rain clear day")
    # how many hours of rain + highest PoP during them
    check_answer_number(judge, answer, "answer_rain_hours", "7",
                        label="hours of rain in the window")
    check_answer_number(judge, answer, "answer_peak_pop", "60",
                        label="highest PoP during the rain hours")
    # temperature range during the dry stretch before the rain
    check_answer_number(judge, answer, "answer_dry_low", "12",
                        label="dry-stretch low temperature")
    check_answer_number(judge, answer, "answer_dry_high", "23",
                        label="dry-stretch high temperature")
    # r3 gates: overnight low during the rain + Monday afternoon high
    check_answer_number(judge, answer, "answer_overnight_low", "14",
                        label="overnight low during the rain (°C)")
    check_answer_number(judge, answer, "answer_monday_afternoon_high", "20",
                        label="Monday afternoon high after the rain (°C)")
    # 7-day: which day later in the week shows the highest rain chance
    check_answer_any(judge, answer, "answer_week_peak_day",
                     ["thursday", "oct 1", "october 1", "october 1st"],
                     label="highest-rain-chance day later in the week")
    check_answer_number(judge, answer, "answer_week_peak_pop", "70",
                        label="that day's PoP")
    # r3 gate: expected rain amount on that day
    check_answer_any(judge, answer, "answer_week_peak_rain",
                     ["5-10 mm", "5-10mm", "5–10 mm", "5—10 mm", "5 to 10 mm",
                      "5 and 10 mm", "five to ten"],
                     label="expected rain on the highest-rain-chance day")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
