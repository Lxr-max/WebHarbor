#!/usr/bin/env python3
"""Verify SourceForge--3: Help me understand the reported 7-Zip bug where the progress bar reaches 100% before archiving finishes. Find the ticket and report its number, summary, status, creator and priority, then explain the maintainer's reply and whether it identifies a possible cause."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

TASK_ID = "SourceForge--3"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_bugs", r"/p/sevenzip/bugs/")
    check_visited_path(judge, traj, "visited_progress_search", r"/p/sevenzip/bugs/search/.*progress")
    check_visited_path(judge, traj, "visited_ticket_2701", r"/p/sevenzip/bugs/2701/")
    check_answer_phrase(judge, answer, "ticket_summary", 'user interface misleading')
    check_answer_phrase(judge, answer, "ticket_status_open", 'open')
    check_answer_phrase(judge, answer, "ticket_creator", 'Harry Stein')
    check_answer_number(judge, answer, "ticket_priority", 5, 'ticket 2701 priority')
    check_answer_phrase(judge, answer, "owner_reply", 'Maybe your usb was slow')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
