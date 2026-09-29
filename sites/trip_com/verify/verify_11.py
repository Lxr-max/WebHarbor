#!/usr/bin/env python3
"""Verify Trip.com--11.

I'm comparing budget hotels for one night in Miami, 4–5 October 2026. Compare the two cheapest bookable hotels shown in the hotel results, including their guest scores and advertised nightly prices. For each, inspect its lowest-priced room and confirm the room name, bed type and total including taxes on the booking form. Explain which room actually costs less once taxes are included; don't book anything.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--11"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/4648397")
    check_visited_path(judge, traj, "visited_runnerup_detail", r"/hotels/detail/68493916")
    check_answer_phrase(judge, answer, "answer_hotel", 'Hyatt Place Miami Airport East')
    check_answer_number(judge, answer, "answer_score", '8.3')
    check_answer_any(judge, answer, "answer_room_name", ['King Room', 'Accessible King Bed/Tub', 'Accessible King Room With Sofa Bed'])
    check_answer_phrase(judge, answer, "answer_bed", '1 king bed and 1 sofa bed')
    check_answer_money(judge, answer, "answer_room_total", 105.0)
    check_answer_phrase(judge, answer, "answer_runnerup", 'Kompose')
    check_answer_number(judge, answer, "answer_runnerup_score", '8.3')
    check_answer_money(judge, answer, "answer_runnerup_price", 100.0)
    check_answer_phrase(judge, answer, "answer_runnerup_room", 'King Room')
    check_answer_money(judge, answer, "answer_runnerup_room_price", 82.0)
    check_visited_path(judge, traj, "runnerup_booking", r"/hotels/book/(431|434|438)")
    check_answer_money(judge, answer, "runnerup_total", 93)
    check_answer_money(judge, answer, "saving", 12)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
