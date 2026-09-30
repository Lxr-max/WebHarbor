#!/usr/bin/env python3
"""Verify Qatar Airways--14: I'm choosing a seat for QR105 from Doha to London Heathrow on 24 September 2026. Use the flight status and fleet information to identify the aircraft, whether it has Qsuite, its total seat count, and the Business and Economy row ranges so I know which cabin rows to consider."""
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

TASK_ID = "Qatar Airways--14"


SEATS = 283


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_status_by_route",
                navigated_flight_status(traj, mode="route", origin="DOH", dest="LHR"),
                "required: flight-status by route DOH->LHR")
    judge.check("visited_a350_fleet", navigated_fleet(traj, "Airbus-A350-900"),
                "required: /en/our-fleet/Airbus-A350-900.html")
    judge.check("answer_aircraft", contains_all(answer, ["A350-900"]),
                "expected the Airbus A350-900 operating QR105")
    judge.check("answer_qsuite", contains_all(answer, ["Qsuite"]),
                "expected Qsuite mentioned for the A350-900")
    judge.check("answer_seat_count", contains_amount(answer, SEATS),
                f"expected the A350-900 total seat count {SEATS}")
    judge.check("answer_business_rows", contains_all(answer, ["1-8", "1–8"]),
                "expected Business Class rows 1-8")
    judge.check("answer_economy_rows", contains_all(answer, ["30-51", "30–51"]),
                "expected Economy rows 30-51")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
