#!/usr/bin/env python3
"""Verify Qatar Airways--11: Help me choose between Doha and Muscat for a cultural city break using Qatar Airways' destination guides. I want to visit the Museum of Islamic Art and spend the rest of the day by the water. Recommend the city that fits, with two waterfront activities from its guide, and explain the alternative by naming Muscat's heritage museum and the beach its guide recommends for a sunset swim."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, added_booking_matching, booking_legs,
                        booking_passengers, check_only_tables_changed, check_read_only,
                        check_seed_identity, check_trajectory_identity, contains_all,
                        contains_any, contains_amount, contains_time,
                        entered_text_containing, final_answer, find_booking,
                        navigated_baggage, navigated_boarding_pass, navigated_checkin,
                        navigated_checkin_lookup, navigated_confirmation,
                        navigated_destination_guide, navigated_destinations,
                        navigated_fleet, navigated_flight_status, navigated_help,
                        navigated_manage_booking, navigated_manage_lookup,
                        navigated_offer, navigated_passenger_details, navigated_payment,
                        navigated_pc, navigated_search, navigated_select_return,
                        pnr_tokens, row_delta, run_verifier, user_by_email)

TASK_ID = "Qatar Airways--11"

DOHA_SLUG = "flights-to-doha"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    judge.check("visited_muscat_guide", navigated_destination_guide(traj, "flights-to-muscat"))
    judge.check("muscat_heritage", contains_any(answer, ["Bait Al-Zubair", "Bait al Zubair"]))
    judge.check("muscat_beach", contains_all(answer, ["Qurum Beach"]))

    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_doha_guide",
                navigated_destination_guide(traj, DOHA_SLUG),
                f"required: /en/destinations/{DOHA_SLUG}.html")
    judge.check("answer_city", contains_all(answer, ["Doha"]),
                "expected city Doha")
    judge.check("answer_activities",
                contains_any(answer, ["Corniche"]) and
                (contains_any(answer, ["dhow", "boat ride"]) or contains_any(answer, ["Pearl"])),
                "expected two Activities: the Corniche stroll/dhow boat ride and The Pearl")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
