#!/usr/bin/env python3
"""Verify SourceForge--0.

I'm choosing a free file archiver for Windows. Search the open source directory for "file compression", sort by Most Popular, and compare the top two results against 7-Zip. For each of the three projects report the weekly download count, registered date, and license from the project page, plus the average rating and total review count from its Reviews page. Finally, which of the three was updated most recently?
"""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any, check_answer_phrase_near)

TASK_ID = "SourceForge--0"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "sorted_search", r"/directory/\?q=file(\+|%20)compression.*sort=popular")
    check_visited_path(judge, traj, "visited_mingw", r"/projects/mingw/")
    check_visited_path(judge, traj, "visited_autoclicker", r"/projects/orphamielautoclicker/")
    check_visited_path(judge, traj, "visited_7zip", r"/projects/sevenzip/")
    check_visited_path(judge, traj, "visited_reviews_for_ratings", r"/projects/(mingw|orphamielautoclicker|sevenzip)/reviews/")
    check_answer_phrase(judge, answer, "mingw_name", 'MinGW')
    check_answer_number(judge, answer, "mingw_week", '3,600,000', 'MinGW weekly downloads', subject='MinGW', competitors=['AutoClicker', '7-Zip'], near='weekly')
    check_answer_phrase_near(judge, answer, "mingw_reg", '2000-02-09', subject='MinGW', competitors=['AutoClicker', '7-Zip'])
    check_answer_phrase_near(judge, answer, "mingw_license", 'GPLv3', subject='MinGW', competitors=['AutoClicker', '7-Zip'], near='licen')
    check_answer_number(judge, answer, "mingw_rating", '4.6', 'MinGW rating', subject='MinGW', competitors=['AutoClicker', '7-Zip'], near='rating')
    check_answer_number(judge, answer, "mingw_reviews", 171, 'MinGW review count', subject='MinGW', competitors=['AutoClicker', '7-Zip'], near='reviews?')
    check_answer_phrase(judge, answer, "auto_name", 'AutoClicker')
    check_answer_number(judge, answer, "auto_week", '768,800', 'AutoClicker weekly downloads', subject='AutoClicker', competitors=['MinGW', '7-Zip'], near='weekly')
    check_answer_phrase_near(judge, answer, "auto_reg", '2014-06-19', subject='AutoClicker', competitors=['MinGW', '7-Zip'])
    check_answer_phrase_near(judge, answer, "auto_license", 'Creative Commons Attribution Non-Commercial', subject='AutoClicker', competitors=['MinGW', '7-Zip'], near='licen')
    check_answer_number(judge, answer, "auto_rating", '4.9', 'AutoClicker rating', subject='AutoClicker', competitors=['MinGW', '7-Zip'], near='rating')
    check_answer_number(judge, answer, "auto_reviews", 221, 'AutoClicker review count', subject='AutoClicker', competitors=['MinGW', '7-Zip'], near='reviews?')
    check_answer_number(judge, answer, "sz_week", 23587, '7-Zip weekly downloads', subject='7-Zip', competitors=['MinGW', 'AutoClicker'], near='weekly')
    check_answer_phrase_near(judge, answer, "sz_reg", '2000-11-10', subject='7-Zip', competitors=['MinGW', 'AutoClicker'])
    check_answer_phrase_near(judge, answer, "sz_license", 'GNU Library or Lesser General Public License version 2.0', subject='7-Zip', competitors=['MinGW', 'AutoClicker'], near='licen')
    check_answer_number(judge, answer, "sz_rating", '4.8', '7-Zip rating', subject='7-Zip', competitors=['MinGW', 'AutoClicker'], near='rating')
    check_answer_number(judge, answer, "sz_reviews", 831, '7-Zip review count', subject='7-Zip', competitors=['MinGW', 'AutoClicker'], near='reviews?')
    check_answer_phrase_near(judge, answer, "sz_updated_more_recent", '2026-09-04', subject='7-Zip', competitors=['MinGW', 'AutoClicker'], near='updat|recent')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
