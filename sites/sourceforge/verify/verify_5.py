#!/usr/bin/env python3
"""Verify SourceForge--5.

I'm researching download trends. From the Top Downloaded Projects page, report the #1 project all-time with its figure, the #1 project for last week with its figure, and where 7-Zip ranks all-time with its total. Open the top three all-time projects' pages and report each one's registered date and weekly downloads, and the two #1s' licenses. Report all three top projects' average ratings and review counts from their Reviews pages. Finally, from 7-Zip's own page report its last update date and total review count, and its average rating from its Reviews page.
"""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any, check_answer_phrase_near)

TASK_ID = "SourceForge--5"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_top", r"/top")
    check_visited_path(judge, traj, "visited_corefonts", r"/projects/corefonts/")
    check_visited_path(judge, traj, "visited_mingw", r"/projects/mingw/")
    check_visited_path(judge, traj, "visited_npp", r"/projects/npppluginmgr/")
    check_visited_path(judge, traj, "visited_corefonts_reviews", r"/projects/corefonts/reviews/")
    check_visited_path(judge, traj, "visited_mingw_reviews", r"/projects/mingw/reviews/")
    check_visited_path(judge, traj, "visited_npp_reviews", r"/projects/npppluginmgr/reviews/")
    check_visited_path(judge, traj, "visited_7zip", r"/projects/sevenzip/")
    check_visited_path(judge, traj, "visited_7zip_reviews", r"/projects/sevenzip/reviews/")
    check_answer_phrase(judge, answer, "alltime_no1", 'TrueType core fonts')
    check_answer_phrase_near(judge, answer, "alltime_no1_downloads", '3.3B', subject='TrueType', competitors=['MinGW', '7-Zip'])
    check_answer_phrase(judge, answer, "weekly_no1", 'MinGW')
    check_answer_phrase_near(judge, answer, "weekly_no1_downloads", '3.6M', subject='MinGW', competitors=['TrueType', '7-Zip'])
    check_answer_number(judge, answer, "sz_alltime_rank", '10', '10', subject='7-Zip', competitors=['corefonts', 'MinGW', 'Notepad++ Plugin Manager'], near='all-time|rank|#')
    check_answer_any(judge, answer, "sz_alltime_total", ['430M', '430.1M', '430,100,000'], '7-Zip all-time total as displayed', subject='7-Zip', competitors=['corefonts', 'MinGW', 'Notepad++ Plugin Manager'], near='430|all-time|total')
    check_answer_phrase_near(judge, answer, "corefonts_reg", '2001-08-22', subject='corefonts', competitors=['MinGW', 'Notepad++ Plugin Manager', '7-Zip'])
    check_answer_phrase_near(judge, answer, "mingw_reg", '2000-02-09', subject='MinGW', competitors=['corefonts', 'Notepad++ Plugin Manager', '7-Zip'])
    check_answer_phrase_near(judge, answer, "npp_reg", '2011-11-29', subject='Notepad++ Plugin Manager', competitors=['corefonts', 'MinGW', '7-Zip'])
    check_answer_number(judge, answer, "corefonts_week", '3,000,000', 'corefonts weekly downloads', subject='corefonts', competitors=['MinGW', 'Notepad++ Plugin Manager', '7-Zip'], near='weekly')
    check_answer_number(judge, answer, "mingw_week", '3,600,000', 'MinGW weekly downloads', subject='MinGW', competitors=['corefonts', 'Notepad++ Plugin Manager', '7-Zip'], near='weekly')
    check_answer_number(judge, answer, "npp_week", '109,095', 'Notepad++ Plugin Manager weekly downloads', subject='Notepad++ Plugin Manager', competitors=['corefonts', 'MinGW', '7-Zip'], near='weekly')
    check_answer_phrase_near(judge, answer, "corefonts_license", 'GPLv2', subject='corefonts', competitors=['MinGW', 'Notepad++ Plugin Manager', '7-Zip'], near='licen')
    check_answer_phrase_near(judge, answer, "mingw_license", 'GPLv3', subject='MinGW', competitors=['corefonts', 'Notepad++ Plugin Manager', '7-Zip'], near='licen')
    check_answer_number(judge, answer, "corefonts_rating", '4.1', 'corefonts rating', subject='corefonts', competitors=['MinGW', 'Notepad++ Plugin Manager', '7-Zip'], near='rating')
    check_answer_number(judge, answer, "corefonts_reviews", 46, 'corefonts review count', subject='corefonts', competitors=['MinGW', 'Notepad++ Plugin Manager', '7-Zip'], near='reviews?')
    check_answer_number(judge, answer, "mingw_rating", '4.6', 'MinGW rating', subject='MinGW', competitors=['corefonts', 'Notepad++ Plugin Manager', '7-Zip'], near='rating')
    check_answer_number(judge, answer, "mingw_reviews", 171, 'MinGW review count', subject='MinGW', competitors=['corefonts', 'Notepad++ Plugin Manager', '7-Zip'], near='reviews?')
    check_answer_number(judge, answer, "npp_rating", '4.4', 'Notepad++ Plugin Manager rating', subject='Notepad++ Plugin Manager', competitors=['corefonts', 'MinGW', '7-Zip'], near='rating')
    check_answer_number(judge, answer, "npp_reviews", 64, 'Notepad++ Plugin Manager review count', subject='Notepad++ Plugin Manager', competitors=['corefonts', 'MinGW', '7-Zip'], near='reviews?')
    check_answer_phrase_near(judge, answer, "sz_updated", '2026-09-04', subject='7-Zip', competitors=['corefonts', 'MinGW', 'Notepad++ Plugin Manager'], near='updat')
    check_answer_number(judge, answer, "sz_total_reviews", 831, '7-Zip total review count on its project page', subject='7-Zip', competitors=['corefonts', 'MinGW', 'Notepad++ Plugin Manager'], near='total|reviews')
    check_answer_number(judge, answer, "sz_rating", '4.8', '7-Zip rating from its Reviews page', subject='7-Zip', competitors=['corefonts', 'MinGW', 'Notepad++ Plugin Manager'], near='rating')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
