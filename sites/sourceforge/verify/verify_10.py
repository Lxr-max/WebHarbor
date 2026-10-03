#!/usr/bin/env python3
"""Verify SourceForge--10: Compare this month's Staff Choice and Community Choice projects to help me choose one to try. Report their names, homepage review counts, weekly downloads, update dates and average review ratings. For the Staff Choice, also check the five-star and one-star counts to assess how divided the reviews are."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

TASK_ID = "SourceForge--10"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_homepage", r"localhost:\d+/?$")
    check_visited_path(judge, traj, "visited_7zip", r"/projects/sevenzip/")
    check_visited_path(judge, traj, "visited_sz_reviews", r"/projects/sevenzip/reviews/")
    check_visited_path(judge, traj, "visited_keepass", r"/projects/keepass/")
    check_visited_path(judge, traj, "visited_kp_reviews", r"/projects/keepass/reviews/")
    check_answer_phrase(judge, answer, "staff_choice", '7-Zip')
    check_answer_phrase(judge, answer, "community_choice", 'KeePass')
    check_answer_number(judge, answer, "staff_reviews", 831, '7-Zip review count')
    check_answer_number(judge, answer, "community_reviews", 606, 'KeePass review count')
    check_answer_number(judge, answer, "sz_week", 23587, '7-Zip weekly downloads')
    check_answer_phrase(judge, answer, "sz_updated", '2026-09-04')
    check_answer_number(judge, answer, "sz_rating", '4.8', '7-Zip rating')
    check_answer_number(judge, answer, "sz_five_star", 765, '7-Zip 5-star count')
    check_answer_number(judge, answer, "sz_one_star", 27, '7-Zip 1-star count')
    check_answer_number(judge, answer, "kp_week", '205,800', 'KeePass weekly downloads')
    check_answer_phrase(judge, answer, "kp_updated", '2026-07-25')
    check_answer_number(judge, answer, "kp_rating", '4.9', 'KeePass rating')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
