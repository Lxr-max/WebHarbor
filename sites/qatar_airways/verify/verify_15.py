#!/usr/bin/env python3
"""Verify Qatar Airways--15: I'm choosing between Economy Lite and Economy Comfort for Doha to Sao Paulo and need room for my luggage. Compare their included checked bags on this piece-concept route, including each bag's weight limit, and find the cost of an extra 23kg piece. Use the Help pages to explain the cabin-baggage allowance that applies to this Brazil trip, including its weight and dimensions, so I can decide what to pack in the cabin."""
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

TASK_ID = "Qatar Airways--15"


EXTRA_RATE = 140
CARRYON_KG = 7


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    judge.check("brazil_cabin_baggage", bool(re.search(r"(?:Brazil|cabin|carry.on)[^.;\n]{0,120}\b10\s*kg\b", answer, re.I)))
    judge.check("brazil_not_general_limit", not re.search(r"(?:Brazil|cabin|carry.on)[^.;\n]{0,80}\b7\s*kg\b", answer, re.I))
    judge.check("cabin_dimensions", bool(re.search(r"50\s*[x×]\s*37\s*[x×]\s*25\s*cm", answer, re.I)))

    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_baggage_comfort",
                navigated_baggage(traj, fare="Economy Comfort", route="americas"),
                "required: baggage checker Economy Comfort / piece concept")
    judge.check("visited_baggage_lite",
                navigated_baggage(traj, fare="Economy Lite", route="americas"),
                "required: baggage checker Economy Lite / piece concept")
    judge.check("visited_help", navigated_help(traj),
                "required: /en/help.html for the carry-on rules")
    judge.check("answer_eco_comfort",
                (contains_amount(answer, 2) or contains_all(answer, ["two"])) and contains_any(answer, ["23kg", "23 kg"]),
                "expected Economy Comfort 2 pieces up to 23kg each")
    judge.check("answer_extra_rate", contains_amount(answer, EXTRA_RATE),
                f"expected the extra-piece rate USD {EXTRA_RATE}")
    judge.check("answer_eco_lite",
                contains_all(answer, ["Lite"]) and
                (contains_any(answer, ["1 piece", "one piece"]) or contains_amount(answer, 1)),
                "expected Economy Lite 1 piece up to 23kg on piece concept")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
