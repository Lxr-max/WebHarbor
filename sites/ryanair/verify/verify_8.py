#!/usr/bin/env python3
"""Verify Ryanair--8.

I've moved and replaced my bank card. Log in to myRyanair as Alice Johnson (alice.j@test.com, password TestPass123!) and update my contact and billing details to +44 7700 900777, 2 Test Lane, Manchester, M1 1AA. Replace the saved Visa with my Mastercard, number 5555 5555 5555 4444, name Alice Johnson, expiry 05/28. Confirm that only the new card remains and it is the default, then log out.
"""
from verify_lib import (Judge, booking_by_ref, check_only_tables_changed,
                        check_seed_rows_preserved, check_signed_in_as, check_trajectory_identity,
                        check_visited_path, contains_amount, contains_any, contains_count,
                        contains_phrase, db_query, final_answer, navigated_to_path,
                        payment_methods_of, run_verifier, user_by_email)

TASK_ID = "Ryanair--8"
EMAIL = "alice.j@test.com"
PHONE = "+44 7700 900777"
ADDRESS = "2 Test Lane"
CITY = "Manchester"
POSTCODE = "M1 1AA"
MALAGA_REF = "T7W3ND"
MALAGA_TOTAL = 311.07
BP_SEAT = "2C"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_signed_in_as(judge, traj, EMAIL)
    check_visited_path(judge, traj, "visited_account", "/gb/en/myryanair/account")
    # profile updates
    alice = user_by_email(after_db, EMAIL)
    judge.check("phone_updated", alice is not None and alice["phone"] == PHONE,
                f"phone={alice and alice['phone']!r}, expected {PHONE!r}")
    judge.check("address_updated",
                alice is not None and alice["address_line1"] == ADDRESS
                and alice["city"] == CITY and alice["postcode"] == POSTCODE,
                f"address=({alice and alice['address_line1']!r}, {alice and alice['city']!r}, "
                f"{alice and alice['postcode']!r})")
    # card swap: exactly one card left, the Mastercard 4444
    cards = payment_methods_of(after_db, alice["id"])
    judge.check("one_saved_card_mastercard_4444",
                len(cards) == 1 and cards[0]["card_type"] == "Mastercard"
                and cards[0]["last4"] == "4444",
                f"cards={[(c['card_type'], c['last4']) for c in cards]!r}")
    judge.check("answer_reports_card_state",
                contains_count(answer, 1) and contains_any(answer, ["mastercard", "4444"]),
                "answer must report 1 saved payment method, the Mastercard ending 4444")
    logged_out = (navigated_to_path(traj, "/gb/en/myryanair/logout")
                  or any("logout" in str(s.get("thought", "")).lower().replace("log out", "logout")
                         or "logout" in str((s.get("params") or {}).get("selector", "")).lower().replace("log out", "logout")
                         for s in traj.get("steps", []) if isinstance(s, dict)))
    judge.check("logged_out", logged_out,
                "required: the logout action (link /gb/en/myryanair/logout)")
    # other users untouched; only alice's row may change
    check_seed_rows_preserved(judge, initial_db, after_db, "users", "id",
                              mutable_fields=("phone", "address_line1", "address_line2",
                                              "city", "postcode"))
    check_only_tables_changed(judge, initial_db, after_db,
                              ("users", "payment_methods"))


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
