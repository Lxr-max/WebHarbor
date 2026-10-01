#!/usr/bin/env python3
"""Verify SpotHero--15: Sign in as Alice Johnson (alice.j@test.com, TestPass123!) and save a parking option for her San Francisco trip. Find the cheapest covered garage near Union Square for October 3, 9 AM–5 PM, check its facility details, then add it to her saved spots. Reopen the saved list and confirm the facility and starting price, keeping her existing saved spots."""
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

TASK_ID = "SpotHero--15"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path(judge, traj, "login", r"/auth/login")
    check_visited_path(judge, traj, "union_square_search", r"/search\?.*search_string=Union")
    check_visited_path(judge, traj, "covered_filter", r"/search\?.*covered=1")
    check_visited_path(judge, traj, "riu_facility_page", r"/facility/6182")
    check_visited_path(judge, traj, "saved_spots_list", r"/account/favorites")
    check_answer_phrase(judge, answer, "spot_riu", '280 Beach St')
    check_answer_number(judge, answer, "price_12_07", '12.07')
    import re
    judge.check("no_false_removal_claim", not re.search(r"(?:spots|Garage|North).{0,100}(?:were all.{0,30}removed|were removed|deleted)", answer, re.I))
    check_favorites_delta(judge, initial_db, after_db, user_id=1,
                          expect_pairs=[(r["user_id"], r["facility_id"]) for r in initial_db.execute("SELECT * FROM favorites WHERE user_id=1")] + [(1, 6182)],
                          allow_readd=[])
    check_only_tables_changed(judge, initial_db, after_db, ('favorites',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
