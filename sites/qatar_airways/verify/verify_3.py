#!/usr/bin/env python3
"""Verify Qatar Airways--3: My colleague is meeting someone on QR004 from London to Doha on 24 September 2026. Check its current status, scheduled departure, estimated arrival and aircraft so they can plan the pickup. The traveller is considering an earlier flight: compare the London–Doha departures that day and identify the earliest option, with its flight number and departure time."""
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

TASK_ID = "Qatar Airways--3"


SCHED_DEP = "15:05"
EST_ARR = "23:47"
EARLIEST_DEP = "08:25"
EARLIEST_FLIGHT = "QR104"
TOTAL_SEATS = 517


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_status_by_number",
                navigated_flight_status(traj, mode="number", number="QR004"),
                "required: flight-status by number QR004")
    judge.check("visited_status_by_route",
                navigated_flight_status(traj, mode="route", origin="LHR", dest="DOH"),
                "required: flight-status by route LHR->DOH")
    judge.check("answer_status", contains_all(answer, ["En route"]),
                "expected the current status En route")
    judge.check("answer_sched_dep", contains_time(answer, SCHED_DEP),
                f"expected scheduled departure {SCHED_DEP}")
    judge.check("answer_est_arr", contains_time(answer, EST_ARR),
                f"expected estimated arrival {EST_ARR}")
    judge.check("answer_aircraft", contains_all(answer, ["A380-800"]),
                "expected the aircraft Airbus A380-800")
    judge.check("answer_earliest_dep", contains_time(answer, EARLIEST_DEP),
                f"expected the earliest London-Doha departure {EARLIEST_DEP}")
    judge.check("answer_earliest_flight", contains_all(answer, [EARLIEST_FLIGHT]),
                f"expected the earliest flight {EARLIEST_FLIGHT}")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
