#!/usr/bin/env python3
"""Verify SpotHero--14: Sign in as Bob Chen (bob.c@test.com, TestPass123!) and update his vehicle to a Honda CR-V Hybrid with license plate WI-BO1180. Save the profile, then sign out and back in to verify the vehicle and plate persisted. Report the saved details."""
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

TASK_ID = "SpotHero--14"


def main(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_package(judge, traj, TASK_ID)
    check_seed_contract(judge, initial_db)
    check_visited_path_count(judge, traj, "login_twice", r"/auth/login", 2)
    check_visited_path_count(judge, traj, "profile_twice", r"/account/profile", 2)
    check_visited_path(judge, traj, "account", r"/account$")
    check_answer_phrase(judge, answer, "plate_updated", 'WI-BO1180')
    check_answer_phrase(judge, answer, "vehicle_updated", 'Honda CR-V Hybrid')
    check_profile_delta(judge, initial_db, after_db, user_id=2,
                        fields={'license_plate': 'WI-BO1180', 'vehicle': 'Honda CR-V Hybrid'})
    check_only_tables_changed(judge, initial_db, after_db, ('users',))
    return judge


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, main))
