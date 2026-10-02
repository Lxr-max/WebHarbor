#!/usr/bin/env python3
"""Verify Ryanair--10.

Help David Kim get ready for his upcoming Rome flight. Log in as david.k@test.com (password TestPass123!), open the booking and complete online check-in. Report the outbound flight number and departure time, the seat shown on the boarding pass and when boarding closes. Find the airport fee for re-issuing the pass so David knows the cost if he cannot present it.
"""
from verify_lib import (Judge, booking_by_ref, check_only_tables_changed, check_seed_rows_preserved,
                        check_signed_in_as, check_trajectory_identity, check_visited_path,
                        contains_amount, contains_any, contains_count, contains_phrase,
                        contains_time, final_answer, payment_methods_of, run_verifier,
                        user_by_email)

TASK_ID = "Ryanair--10"
EMAIL = "david.k@test.com"
PHONE = "+44 7700 900456"
ROME_REF = "R2M6YB"
OUT_FLIGHT = "FR 3942"
OUT_DEP = "20:40"
BP_SEAT = "1A"
TOTAL = 1064.80
REISSUE_FEE = 20.00


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, EMAIL)
    david = user_by_email(after_db, EMAIL)
    cards = payment_methods_of(after_db, david["id"])
    check_visited_path(judge, traj, "visited_rome_booking", f"/gb/en/booking/{ROME_REF}")
    check_visited_path(judge, traj, "visited_checkin", f"/gb/en/check-in/{ROME_REF}")
    check_visited_path(judge, traj, "visited_boarding_pass", f"/gb/en/boarding-pass/{ROME_REF}")
    bk = booking_by_ref(after_db, ROME_REF)
    judge.check("rome_booking_exists", bk is not None, f"ref={ROME_REF}")
    if bk:
        judge.check("rome_checked_in", bool(bk["checked_in"]), f"checked_in={bk['checked_in']!r}")
        judge.check("rome_total", abs(bk["total"] - TOTAL) < 0.011,
                    f"total={bk['total']!r}, expected {TOTAL}")
    judge.check("answer_flight_facts",
                contains_phrase(answer, OUT_FLIGHT) and contains_time(answer, OUT_DEP)
                and contains_phrase(answer, BP_SEAT),
                f"answer must report {OUT_FLIGHT} departing {OUT_DEP} and seat {BP_SEAT}")
    judge.check("answer_boarding_closes",
                contains_phrase(answer, "30 min") or contains_phrase(answer, "30 minutes")
                or contains_phrase(answer, "20:10"),
                "answer must state boarding closes 30 minutes before departure (20:10)")
    check_visited_path(judge, traj, "visited_help_checkin", "/gb/en/r/help/check-in")
    judge.check("answer_reissue_fee_20", contains_amount(answer, REISSUE_FEE),
                f"expected re-issue fee £{REISSUE_FEE:.2f}")
    check_seed_rows_preserved(judge, initial_db, after_db, "users", "id",
                              mutable_fields=("phone",))
    check_only_tables_changed(judge, initial_db, after_db, ("users", "bookings"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
