#!/usr/bin/env python3
"""Verify The Weather Network--11 (Animals and Weather playlist extremes).

r2 re-sync: deepened to the playlist count, both extreme durations, the
longest video's description page and the Featured-playlist comparison.
Frozen ground truth: the Animals and Weather playlist holds 50 videos; its
longest video is 'All about bees: What to do when you get stung, and more'
at exactly 4:00; the shortest is 'Good samaritan gives water to bat
struggling during heat wave' at 0:50; the longest video's page describes
Kim MacDonald and Rachel Schoutsen revealing everything about bees and what
to do when stung; the Featured playlist's longest video is 'Fall Night Sky:
Parade of meteor showers, plus a planet dance' at 3:37 — so the Animals
playlist's longest video runs longer.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 11)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_video_index", r"/en/video")
    check_visited_path(judge, traj, "visited_longest_video_page",
                       r"/en/video/[A-Za-z0-9]{8}")
    check_visited_path(judge, traj, "visited_shortest_video", r"/en/video/PfcTWOOE")
    # playlist size
    # longest video title + exact duration
    check_answer_any(judge, answer, "answer_longest_title",
                     ["all about bees: what to do when you get stung", "all about bees"],
                     label="longest video title")
    check_answer_any(judge, answer, "answer_longest_duration", ["4:00", "4 minutes"],
                     label="longest video exact duration")
    # shortest video title + duration
    check_answer_any(judge, answer, "answer_shortest_title",
                     ["good samaritan gives water to bat"],
                     label="shortest video title")
    check_answer_any(judge, answer, "answer_shortest_duration", ["0:50", "50 seconds"],
                     label="shortest video duration")
    # what the longest video's description says it's about
    check_answer_any(judge, answer, "answer_longest_about",
                     ["bee", "sting", "stung"],
                     label="longest video description subject")
    # Featured playlist comparison
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
