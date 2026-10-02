#!/usr/bin/env python3
"""Verify Trip.com--9.

I'm choosing a New York hotel for a work trip on 20 October and need parking. Check the New York weekend guide: how much lower are Jersey City and Newark rates? Then find the hotels with more than 500 reviews and parking available, rank them by guest score, and report both names and scores. For the higher-scored one, report its two review tags and its cheapest room's price, bed type, breakfast inclusion and free-cancellation deadline, plus the taxes per night shown on that room's booking form. Report the other hotel's cheapest room name and price too.
"""
from verify_lib import (check_answer_any, check_answer_count_at_least,
                        check_answer_money, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_read_only,
                        check_rows_added, check_rows_changed, check_seed_contract,
                        check_set_delta, check_screenshots, check_trajectory_identity,
                        check_visited_any, check_visited_path, final_answer, run_verifier)

TASK_ID = "Trip.com--9"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_screenshots(judge, traj)
    check_visited_path(judge, traj, "visited_guide", r"/guide/nyc-weekend-midrange")
    check_visited_path(judge, traj, "visited_hotel_list", r"/hotels/list\?")
    check_visited_path(judge, traj, "visited_hotel_detail", r"/hotels/detail/105237897")
    check_visited_path(judge, traj, "visited_book_form", r"/hotels/book/124")
    check_visited_path(judge, traj, "visited_second_hotel", r"/hotels/detail/2192841")
    check_answer_phrase(judge, answer, "answer_hotel", 'Motto by Hilton New York City Times Square')
    check_answer_number(judge, answer, "answer_score", '8.7')
    check_answer_number(judge, answer, "answer_reviews", '714')
    check_answer_phrase(judge, answer, "answer_tag_1", 'American breakfast')
    check_answer_phrase(judge, answer, "answer_tag_2", 'Great views')
    check_answer_phrase(judge, answer, "answer_room", 'Flex Room With Wall Bed')
    check_answer_money(judge, answer, "answer_room_price", 202.0)
    check_answer_phrase(judge, answer, "answer_bed", 'queen')
    check_answer_phrase(judge, answer, "answer_breakfast", 'breakfast')
    check_answer_phrase(judge, answer, "answer_cancel_deadline", '11:59 PM, Oct 1')
    check_answer_phrase(judge, answer, "answer_guide_discount", '30-40%')
    check_answer_phrase(judge, answer, "answer_second_hotel", 'DoubleTree')
    check_answer_number(judge, answer, "answer_second_score", '8.4')
    check_answer_money(judge, answer, "answer_taxes_per_night", 34.0)
    check_answer_phrase(judge, answer, "answer_other_room", 'King Room With City View')
    check_answer_money(judge, answer, "answer_other_price", 175.0)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
