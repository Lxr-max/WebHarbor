#!/usr/bin/env python3
"""Verify Trip.com--19.

Use the site search to find the guide about free cancellation and report the deadline it says refundable rates commonly allow and what happens if you cancel after it. Then find the two cheapest bookable Las Vegas hotels under $60 a night for 20-21 October: report both names, guest scores and review counts, and the runner-up's cheapest room name. For the cheapest one, also report its area, whether parking is listed among its amenities, the cancellation deadline shown on its cheapest room, and that room's total for those nights from its booking form.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--19"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_search", r"/search\?")
    check_visited_path(judge, traj, "visited_guide", r"/guide/free-cancellation-guide")
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/718690")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/1")
    check_visited_path(judge, traj, "visited_linq_detail", r"/hotels/detail/1775443")
    check_answer_phrase(judge, answer, "answer_guide_deadline", '11:59 PM')
    check_answer_phrase(judge, answer, "answer_guide_window", 'one to three days')
    check_answer_phrase(judge, answer, "answer_guide_after", 'first night')
    check_answer_phrase(judge, answer, "answer_hotel", 'Harrah')
    check_answer_number(judge, answer, "answer_score", '8.4')
    check_answer_number(judge, answer, "answer_reviews", '536')
    check_answer_phrase(judge, answer, "answer_cancel_deadline", '11:59 PM, Oct 1')
    check_answer_phrase(judge, answer, "answer_runnerup", 'LINQ')
    check_answer_number(judge, answer, "answer_runnerup_reviews", '344')
    check_answer_phrase(judge, answer, "answer_runnerup_room", 'Deluxe Two Double Room')
    check_answer_phrase(judge, answer, "answer_area", 'Las Vegas Strip')
    check_answer_phrase(judge, answer, "answer_parking", 'parking')
    check_answer_money(judge, answer, "answer_room_total", 64.0)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
