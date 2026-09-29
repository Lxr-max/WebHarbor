#!/usr/bin/env python3
"""Verify Qatar Airways--16: Help Carol Davis prepare a medical-assistance request for her booked New York trip. Sign in as carol.d@test.com (password TestPass123!) and retrieve booking QC08BV. Report the passengers and outbound flight/date to identify the trip, then find the required language and submission window for the medical form. Carol is hard of hearing, so include the dedicated support number and its hours. Do not change the booking or submit a request."""
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

TASK_ID = "Qatar Airways--16"


MEDICAL_DAYS = 7
MEDICAL_HOURS = 48
OMAN_DAYS = 19
CERT_MONTHS = 12


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    judge.check("visited_trip", navigated_manage_booking(traj, "QC08BV"))
    judge.check("passengers", contains_all(answer, ["Carol Davis", "James Davis"]))
    judge.check("flight", contains_all(answer, ["QR701"]))
    judge.check("outbound_date", contains_any(answer, ["20 October 2026", "October 20, 2026", "2026-10-20"]))
    judge.check("form_language", contains_all(answer, ["English"]))
    judge.check("support_hours", contains_any(answer, ["24-hour", "24 hour", "24 hours", "24/7", "around the clock"]))

    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    judge.check("visited_help", navigated_help(traj),
                "required: /en/help.html")
    judge.check("answer_support_number",
                contains_all(answer, ["833", "607", "2675"]),
                "expected the hard-of-hearing support number +1 833 607 2675")
    judge.check("answer_medical_window",
                contains_amount(answer, MEDICAL_DAYS) and contains_amount(answer, MEDICAL_HOURS),
                f"expected the medical form window {MEDICAL_DAYS} days / {MEDICAL_HOURS} hours")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
