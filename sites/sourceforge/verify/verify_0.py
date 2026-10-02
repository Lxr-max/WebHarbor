#!/usr/bin/env python3
"""Verify SourceForge--0: I am checking how useful SourceForge's search results are for finding a Windows file archiver. Compare the two most popular results for 'file compression' with 7-Zip: report each project's purpose, license, weekly downloads, registration date, and review rating and count. Explain which results actually fit the archiving requirement and which project was updated most recently."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

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
    check_answer_number(judge, answer, "mingw_week", '3,600,000', 'MinGW weekly downloads')
    check_answer_phrase(judge, answer, "mingw_reg", '2000-02-09')
    check_answer_phrase(judge, answer, "mingw_license", 'GPLv3')
    check_answer_number(judge, answer, "mingw_rating", '4.6', 'MinGW rating')
    check_answer_number(judge, answer, "mingw_reviews", 171, 'MinGW review count')
    check_answer_phrase(judge, answer, "auto_name", 'AutoClicker')
    check_answer_number(judge, answer, "auto_week", '768,800', 'AutoClicker weekly downloads')
    check_answer_phrase(judge, answer, "auto_reg", '2014-06-19')
    check_answer_phrase(judge, answer, "auto_license", 'Creative Commons Attribution Non-Commercial')
    check_answer_number(judge, answer, "auto_rating", '4.9', 'AutoClicker rating')
    check_answer_number(judge, answer, "auto_reviews", 221, 'AutoClicker review count')
    check_answer_number(judge, answer, "sz_week", 23587, '7-Zip weekly downloads')
    check_answer_phrase(judge, answer, "sz_reg", '2000-11-10')
    check_answer_phrase(judge, answer, "sz_license", 'GNU Library or Lesser General Public License version 2.0')
    check_answer_number(judge, answer, "sz_rating", '4.8', '7-Zip rating')
    check_answer_number(judge, answer, "sz_reviews", 831, '7-Zip review count')
    check_answer_phrase(judge, answer, "sz_updated_more_recent", '2026-09-04')
    from comparison_checks import entity_numbers
    labels = [r"MinGW(?: - Minimalist GNU for Windows)?", r"AutoClicker", r"7-Zip"]
    for i, values in enumerate([(3600000, 4.6, 171), (768800, 4.9, 221), (23587, 4.8, 831)]):
        entity_numbers(judge, answer, "project_values_"+str(i), [labels[i]], labels[:i]+labels[i+1:], values)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
