#!/usr/bin/env python3
"""Verify StubHub--9.

Seattle Opera's production of Salome has performances on multiple dates. Find every Salome event listed on the site and report each with its date and get-in price. Compare the two earliest performances: which one has more listings, and which has the lower get-in price? Report the venue's full name and city as shown on the event pages, and the section of the cheapest listing for each of those two dates.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--9"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "searched_salome", r"/search\?q=salome")
    check_visited_path(judge, traj, "visited_salome_1017", r"/seattle-opera-seattle-tickets-10-17-2026/event/161306164")
    check_visited_path(judge, traj, "visited_salome_1023", r"/seattle-opera-seattle-tickets-10-23-2026/event/161306174")
    check_visited_path(judge, traj, "visited_salome_1025", r"/seattle-opera-seattle-tickets-10-25-2026/event/161306180")
    check_visited_path(judge, traj, "visited_salome_1028", r"/seattle-opera-seattle-tickets-10-28-2026/event/161306184")
    check_visited_path(judge, traj, "visited_salome_1031", r"/seattle-opera-seattle-tickets-10-31-2026/event/161306189")
    
    for date, price in (("10-17", 123), ("10-23", 120), ("10-25", 153),
                       ("10-28", 89), ("10-31", 117)):
        check_answer_number(judge, answer, f"getin_{date}", price)
    check_answer_number(judge, answer, "first_listings", 27)
    check_answer_number(judge, answer, "second_listings", 24)
    # audit fix (2026-09-26): accept the date as displayed on the page
    # ("Oct 17") as well as the URL-slug form ("10-17"); both name the same
    # (correct) performance.
    judge.check("more_listings_verdict",
                "10-17" in answer or "Oct 17" in answer or "October 17" in answer,
                "answer must name the Oct 17 performance as having more listings (27 vs 24)")
    check_answer_number(judge, answer, "lower_getin", 120)
    check_answer_phrase(judge, answer, "venue_full", "McCaw Hall")
    check_answer_phrase(judge, answer, "venue_city", "Seattle")
    check_answer_phrase(judge, answer, "first_cheapest_section", "ST 41")
    check_answer_phrase(judge, answer, "second_cheapest_section", "ST 42")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
