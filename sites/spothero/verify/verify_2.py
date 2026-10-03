#!/usr/bin/env python3
"""Verify SpotHero--2: I am choosing between the Tyler Childers show on October 2 and JUNGLE on October 3 at Climate Pledge Arena. I need the option whose parking opens earlier in the evening. Compare their event parking windows, then book the cheapest parking for that show as show.night@example.com. Report the show, both windows, the facility, walking time and total."""
import sys

from verify_lib import (Judge, check_package, check_seed_contract,
                        check_visited_path, check_visited_path_count,
                        check_answer_phrase,
                        check_answer_number, check_answer_any_number,
                        check_answer_any, check_only_tables_changed,
                        check_reservations_delta, check_any_new_reservation,
                        check_payment_methods_delta, check_profile_delta,
                        check_favorites_delta, check_new_user, final_answer,
                        run_verifier)

TASK_ID = "SpotHero--2"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "arena_destination", r"/destination/seattle/climate-pledge-arena-parking")
    check_visited_path(judge, traj, "tyler_childers_event_search", r"/search\?kind=event&id=1240368")
    check_visited_path(judge, traj, "jungle_event_search", r"/search\?kind=event&id=1307354")
    check_visited_path(judge, traj, "event_price_sort", r"/search\?kind=event&id=1240368.*sort=price")
    check_visited_path(judge, traj, "checkout", r"/purchase/hourly\?facility=164512")
    check_visited_path(judge, traj, "confirmation", r"/purchase/confirmation/SH-")
    check_answer_phrase(judge, answer, "earlier_show", 'Tyler Childers')
    check_answer_phrase(judge, answer, "earlier_window_start", '5:30 PM')
    check_answer_phrase(judge, answer, "earlier_window_end", '11:30 PM')
    check_answer_phrase(judge, answer, "jungle_window", '6:45 PM')
    check_answer_phrase(judge, answer, "garage_named", '5 W Harrison')
    check_answer_phrase(judge, answer, "walk_time", '3 min')
    check_answer_number(judge, answer, "total", '7.49')
    check_reservations_delta(judge, initial_db, after_db, answer,
                             expect_added={'facility_id': 164512, 'kind': 'event', 'total': 7.49, 'email': 'show.night@example.com', 'starts': '2026-10-02T17:30', 'ends': '2026-10-02T23:30', 'promo': '', 'user_id': None, 'status': 'upcoming'},
                             expect_updated=None)
    check_only_tables_changed(judge, initial_db, after_db, ('reservations',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
