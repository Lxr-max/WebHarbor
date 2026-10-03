#!/usr/bin/env python3
"""Verify StubHub--8.

Browse the Theater category and list every subcategory it contains. Then open the Comedy subcategory and report its three soonest events with performer, date, and city. Open each of those three event pages and report each one's get-in price, total listing count, and venue name. Which of the three events has the most available listings?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--8"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_comedy_subcategory", r"/comedy-tickets/category/209")
    check_visited_path(judge, traj, "visited_rocky_horror", r"/the-rocky-horror-show-new-york-tickets-9-26-2026/event/161069710")
    check_visited_path(judge, traj, "visited_little_shop", r"/little-shop-of-horrors-la-mirada-tickets-9-26-2026/event/161174556")
    check_visited_path(judge, traj, "visited_garry_starr", r"/garry-starr-new-york-tickets-9-26-2026/event/162068544")
    
    for sub in ("Musicals", "Plays", "Comedy", "Family", "Classical", "Broadway"):
        check_answer_phrase(judge, answer, f"subcategory_{sub.lower()}", sub)
    judge.check("subcategory_dance_ballet",
                "Dance" in answer and ("Ballet" in answer or "Dance / Ballet" in answer),
                "answer must list the Dance / Ballet subcategory")
    check_answer_phrase(judge, answer, "comedy_event_1", "Rocky Horror")
    check_answer_phrase(judge, answer, "comedy_event_2", "Little Shop of Horrors")
    check_answer_phrase(judge, answer, "comedy_event_3", "Garry Starr")
    check_answer_number(judge, answer, "rocky_getin", 104)
    check_answer_number(judge, answer, "rocky_count", 14)
    check_answer_number(judge, answer, "little_shop_getin", 400)
    check_answer_number(judge, answer, "little_shop_count", 3)
    check_answer_number(judge, answer, "garry_getin", 162)
    check_answer_number(judge, answer, "garry_count", 24)
    judge.check("most_listings_verdict", "Garry Starr" in answer,
                "answer must name Garry Starr as the event with the most listings")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
