#!/usr/bin/env python3
"""Verify Qatar Airways--12: Help me choose between Seoul and Tokyo for a walking and culture holiday using Qatar Airways' guides. I particularly want to visit the Yayoi Kusama Museum. Compare Seoul's city-wall walk, traditional village and palace with a Secret Garden against Tokyo's museum, recommended sushi market and park for jogging or picnics. Include the full city-wall trail's length and say which destination meets my museum priority."""
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

TASK_ID = "Qatar Airways--12"


WALL_KM = "18.6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_seoul_guide",
                navigated_destination_guide(traj, "flights-to-seoul"),
                "required: /en/destinations/flights-to-seoul.html")
    judge.check("visited_tokyo_guide",
                navigated_destination_guide(traj, "flights-to-tokyo"),
                "required: /en/destinations/flights-to-tokyo.html")
    judge.check("answer_kusama_city",
                contains_all(answer, ["Tokyo"]) and contains_all(answer, ["Kusama"]),
                "expected Tokyo named for the Yayoi Kusama Museum")
    judge.check("answer_wall_km", contains_all(answer, [WALL_KM]),
                f"expected the Seoul City Wall Trail length {WALL_KM} km")
    judge.check("answer_hanok_village",
                contains_all(answer, ["Bukchon"]),
                "expected Bukchon Hanok Village from Seoul's Activities")
    judge.check("answer_palace",
                contains_all(answer, ["Changdeokgung"]),
                "expected Changdeokgung from Seoul's Things to do")
    judge.check("answer_sushi_market",
                contains_all(answer, ["Tsukiji"]),
                "expected the Tsukiji Outer Market from Tokyo's Food section")
    judge.check("answer_park",
                contains_all(answer, ["Yoyogi"]),
                "expected Yoyogi Park from Tokyo's Activities")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
