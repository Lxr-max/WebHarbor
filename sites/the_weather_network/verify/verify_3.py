#!/usr/bin/env python3
"""Verify The Weather Network--3 (two Polo articles in severe weather news).

r3 incremental re-sync (onto the deepened T3 @ 2d15effd): the task now also
asks for Patricia's top winds (~345 km/h), how far Polo's central pressure
fell in 24 hours (88 mb, stated in the NOAA eye-footage article), and the
eye-footage piece's author and publish date (Nathan Howes, Sep. 26, 2026).
Frozen ground truth: 'Polo cements status as Pacific's second-most intense
hurricane' — the only eastern-Pacific hurricane with a lower central
pressure is Hurricane Patricia (872 mb, October 2015); Polo reached peak
intensity on Tuesday, Sept. 22 with maximum sustained winds of 285 km/h;
its top embedded video is 'Hurricane Polo, one of the Eastern Pacific's
most intense hurricanes'. The second article, 'WATCH: Inside the eye of
Polo as it grows into a historic hurricane' (NOAA footage), embeds 'See
the view inside Hurricane Polo as it became a monster storm' at the top.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--3"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_severe_listing",
                       r"/en/news/weather/severe")
    check_visited_path(judge, traj, "visited_polo_cements",
                       r"/en/news/weather/severe/polo-cements")
    check_visited_path(judge, traj, "visited_polo_eye",
                       r"/en/news/weather/severe/inside-a-beast")
    # the only eastern-Pacific hurricane with lower central pressure + value
    check_answer_any(judge, answer, "answer_lower_pressure_hurricane",
                     ["patricia"], label="lower-pressure hurricane")
    check_answer_number(judge, answer, "answer_pressure_mb", "872",
                        label="Patricia's pressure (mb)")
    # peak intensity + max sustained winds
    check_answer_any(judge, answer, "answer_peak_date",
                     ["sept. 22", "sept 22", "september 22", "tuesday, sept", "22nd"],
                     label="peak intensity date")
    check_answer_number(judge, answer, "answer_max_winds", "285",
                        label="maximum sustained winds (km/h)")
    # r3 gates: Patricia's top winds + Polo's 24-hour central pressure drop
    check_answer_number(judge, answer, "answer_patricia_top_winds", "345",
                        label="Patricia's top winds (km/h)")
    check_answer_number(judge, answer, "answer_pressure_drop_24h", "88",
                        label="Polo's central pressure drop in 24 hours (mb)")
    # video titles at the top of each article
    check_answer_any(judge, answer, "answer_video_title_article1",
                     ["hurricane polo, one of the eastern pacific's most intense hurricanes",
                      "one of the eastern pacific's most intense hurricanes"],
                     label="video title on the Polo-cements article")
    check_answer_any(judge, answer, "answer_video_title_article2",
                     ["see the view inside hurricane polo"],
                     label="video title on the inside-the-eye article")
    # r3 gates: eye-footage article author + publish date
    check_answer_any(judge, answer, "answer_eye_author", ["nathan howes"],
                     label="eye-footage article author")
    check_answer_any(judge, answer, "answer_eye_date",
                     ["sep. 26, 2026", "sept. 26, 2026", "september 26, 2026",
                      "sep 26, 2026", "sept 26, 2026", "sep. 26", "sept. 26",
                      "september 26"],
                     label="eye-footage article publish date")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
