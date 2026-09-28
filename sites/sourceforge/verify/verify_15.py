#!/usr/bin/env python3
"""Verify SourceForge--15.

Auditing 7-Zip's security record. Search the Bugs tracker for tickets mentioning "CVE" and report how many the search returns, the ticket numbers and summaries of the two newest, and each one's status and priority. Open the lowest-numbered CVE ticket and report who owns it and its creation date. Then find the Open Discussion thread where a user says a vulnerability scanner flagged version 26.02 as unsafe, and report its subject, creator, and post count. Finally, report the tracker's open ticket count from the sidebar.
"""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any, check_answer_phrase_near)

TASK_ID = "SourceForge--15"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_cve_search", r"/p/sevenzip/bugs/search/.*CVE")
    check_visited_path(judge, traj, "visited_ticket_2681", r"/p/sevenzip/bugs/2681/")
    check_visited_path(judge, traj, "visited_ticket_2670", r"/p/sevenzip/bugs/2670/")
    check_visited_path(judge, traj, "visited_ticket_2669", r"/p/sevenzip/bugs/2669/")
    check_visited_path(judge, traj, "visited_forum", r"/p/sevenzip/discussion/45797/")
    check_answer_number(judge, answer, "cve_ticket_count", 3, 'CVE search results', subject='CVE', competitors=['2681', '2670', '2669'], near='return|ticket')
    check_answer_phrase_near(judge, answer, "cve_newest_1", '2681', subject='CVE-2026-58052', competitors=['CVE-2026-48102', '2669'])
    check_answer_phrase(judge, answer, "cve_newest_1_summary", 'CVE-2026-58052')
    check_answer_phrase_near(judge, answer, "cve_newest_2", '2670', subject='CVE-2026-48102', competitors=['CVE-2026-58052', '2669'])
    check_answer_phrase(judge, answer, "cve_newest_2_summary", 'CVE-2026-48102')
    check_answer_phrase_near(judge, answer, "ticket_status_open", 'open', subject='2681', competitors=['2670', '2669'], near='open')
    check_answer_number(judge, answer, "cve_newest_1_priority", 7, 'ticket 2681 priority', subject='2681', competitors=['2670', '2669', 'Barcikowski'], near='priorit')
    check_answer_number(judge, answer, "cve_newest_2_priority", 7, 'ticket 2670 priority', subject='2670', competitors=['2681', '2669', 'Barcikowski'], near='priorit')
    check_answer_phrase_near(judge, answer, "cve_lowest", '2669', subject='2669', competitors=['2681', '2670'], near='own|creat|Igor')
    check_answer_phrase(judge, answer, "cve_lowest_owner", 'Igor Pavlov')
    check_answer_phrase_near(judge, answer, "cve_lowest_created", '2026-06-10', subject='2669', competitors=['2681', '2670'])
    check_answer_phrase(judge, answer, "vuln_thread_subject", 'vulnerability scanner flagged version 26.02 as unsafe')
    check_answer_phrase(judge, answer, "vuln_thread_creator", 'Robert Barcikowski')
    check_answer_number(judge, answer, "vuln_thread_posts", 7, 'vulnerability thread post count', subject='Barcikowski', competitors=['2681', '2670', '2669'], near='posts?')
    check_answer_number(judge, answer, "open_tickets", 31, 'open ticket count', subject='sidebar', competitors=['2681', '2670', '2669', 'Barcikowski'], near='open')
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
