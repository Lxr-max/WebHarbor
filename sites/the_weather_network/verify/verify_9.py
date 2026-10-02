#!/usr/bin/env python3
"""Verify The Weather Network--9 (Harvest Moon article + video + meteor chain).

r2 re-sync: deepened to the NASA double name, the embedded video page and
the meteor-shower article. Frozen ground truth: headline 'The Harvest Moon
lights up our night sky this weekend'; fullest at 12:49 p.m. EDT on the
26th (Sat Sep 26); traditionally named after the corn harvest (Corn Moon);
NASA's two informal names: GRAIL Moon and LADEE Moon; embedded video 'Your
guide to September's night sky'; the linked meteor-shower-season article
says the Draconids peak first this fall (Oct. 8).
"""
from verify_lib import (check_answer_any, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--9"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_harvest_article",
                       r"/en/news/science/space/full-corn-moon-harvest-moon")
    check_visited_path(judge, traj, "visited_embedded_video",
                       r"/en/video/")
    check_visited_path(judge, traj, "visited_meteor_article",
                       r"/en/news/weather/seasonal/autumn-the-season-of-meteor-showers")
    # headline
    check_answer_any(judge, answer, "answer_headline",
                     ["the harvest moon lights up our night sky this weekend"],
                     label="exact headline")
    # fullest moment
    check_answer_any(judge, answer, "answer_fullest_time",
                     ["12:49"], label="fullest time")
    check_answer_any(judge, answer, "answer_fullest_date",
                     ["september 26", "sep 26", "26th", "the 26th", "saturday"],
                     label="fullest date")
    # traditional name
    check_answer_any(judge, answer, "answer_traditional_name",
                     ["corn harvest", "corn moon", "harvesting corn"],
                     label="traditional name basis")
    # NASA's two informal names
    check_answer_any(judge, answer, "answer_nasa_name_1", ["grail"], label="GRAIL Moon")
    check_answer_any(judge, answer, "answer_nasa_name_2", ["ladee"], label="LADEE Moon")
    # embedded video title
    check_answer_any(judge, answer, "answer_video_title",
                     ["your guide to september's night sky", "your guide to september’s night sky"],
                     label="embedded video title")
    # first-peaking meteor shower this fall
    check_answer_any(judge, answer, "answer_first_shower", ["draconid"],
                     label="meteor shower peaking first this fall")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
