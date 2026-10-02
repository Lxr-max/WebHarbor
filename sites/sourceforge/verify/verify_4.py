#!/usr/bin/env python3
"""Verify SourceForge--4: I want to see whether other 7-Zip users have requested dark mode for accessibility reasons before posting my own request. Compare the dark-mode request with the older 'Dark Theme' discussion: identify each thread's creator, opening argument, post count and view count, and give the newer request's creation date. Explain the health reason raised in the newer request."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

TASK_ID = "SourceForge--4"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_forum", r"/p/sevenzip/discussion/45797/")
    check_visited_path(judge, traj, "visited_darkmode_thread", r"/thread/0f17be73d3/")
    check_visited_path(judge, traj, "visited_darktheme_thread", r"/thread/768a550c16/")
    check_answer_phrase(judge, answer, "thread_subject", 'Dark Mode')
    check_answer_phrase(judge, answer, "thread_creator", 'Carlos Nunes')
    check_answer_phrase(judge, answer, "thread_created", 'Tue Jul 08, 2025')
    check_answer_number(judge, answer, "thread_posts", 4, 'Dark Mode posts')
    check_answer_number(judge, answer, "thread_views", '3,206', 'Dark Mode views')
    check_answer_phrase(judge, answer, "darkmode_health_reason", 'greatly facilitates eye comfort')
    check_answer_phrase(judge, answer, "darktheme_creator", 'kb0000001')
    check_answer_number(judge, answer, "darktheme_posts", 18, 'Dark Theme posts')
    check_answer_number(judge, answer, "darktheme_views", '9,620', 'Dark Theme views')
    check_answer_phrase(judge, answer, "darktheme_opening_post", 'Dark Theme')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
