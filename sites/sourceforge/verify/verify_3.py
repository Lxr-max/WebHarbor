#!/usr/bin/env python3
"""Verify SourceForge--3.

A coworker filed a 7-Zip bug about the progress bar reaching 100% while archiving was still running. Find that ticket in the Bugs tracker and report its number, summary, status, creator, and priority, and summarize the project owner's reply. Also search the tracker for "CVE" and report how many tickets that search returns and the ticket numbers, summaries, and priorities of the two newest. Open the lowest-numbered CVE ticket and report who owns it and its creation date. Finally, report the tracker's open ticket count from the sidebar.
"""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any, check_answer_phrase_near)

TASK_ID = "SourceForge--3"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_bugs", r"/p/sevenzip/bugs/")
    check_visited_path(judge, traj, "visited_progress_search", r"/p/sevenzip/bugs/search/.*progress")
    check_visited_path(judge, traj, "visited_ticket_2701", r"/p/sevenzip/bugs/2701/")
    check_visited_path(judge, traj, "visited_cve_search", r"/p/sevenzip/bugs/search/.*CVE")
    check_visited_path(judge, traj, "visited_ticket_2681", r"/p/sevenzip/bugs/2681/")
    check_visited_path(judge, traj, "visited_ticket_2670", r"/p/sevenzip/bugs/2670/")
    check_visited_path(judge, traj, "visited_ticket_2669", r"/p/sevenzip/bugs/2669/")
    check_answer_phrase(judge, answer, "ticket_summary", 'user interface misleading')
    check_answer_phrase_near(judge, answer, "ticket_status_open", 'open', subject='2701', competitors=['2681', '2670', '2669'], near='status')
    check_answer_phrase(judge, answer, "ticket_creator", 'Harry Stein')
    check_answer_number(judge, answer, "ticket_priority", 5, 'ticket 2701 priority', subject='2701', competitors=['2681', '2670', '2669'], near='priorit')
    check_answer_phrase(judge, answer, "owner_reply", 'Maybe your usb was slow')
    check_answer_number(judge, answer, "cve_ticket_count", 3, 'CVE search results', subject='CVE', competitors=['2701', '2681', '2670', '2669'], near='return|ticket')
    check_answer_phrase_near(judge, answer, "cve_newest_1", '2681', subject='CVE-2026-58052', competitors=['CVE-2026-48102', '2669'])
    check_answer_phrase(judge, answer, "cve_newest_1_summary", 'CVE-2026-58052')
    check_answer_number(judge, answer, "cve_newest_1_priority", 7, 'ticket 2681 priority', subject='2681', competitors=['2701', '2670', '2669'], near='priorit')
    check_answer_phrase_near(judge, answer, "cve_newest_2", '2670', subject='CVE-2026-48102', competitors=['CVE-2026-58052', '2669'])
    check_answer_phrase(judge, answer, "cve_newest_2_summary", 'CVE-2026-48102')
    check_answer_number(judge, answer, "cve_newest_2_priority", 7, 'ticket 2670 priority', subject='2670', competitors=['2701', '2681', '2669'], near='priorit')
    check_answer_phrase_near(judge, answer, "cve_lowest", '2669', subject='2669', competitors=['2681', '2670'], near='own|creat|Igor')
    check_answer_phrase(judge, answer, "cve_lowest_owner", 'Igor Pavlov')
    check_answer_phrase_near(judge, answer, "cve_lowest_created", '2026-06-10', subject='2669', competitors=['2681', '2670'])
    check_answer_number(judge, answer, "open_tickets", 31, 'open ticket count', subject='sidebar', competitors=['2701', '2681', '2670', '2669'], near='open')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
