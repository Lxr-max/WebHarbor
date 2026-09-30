#!/usr/bin/env python3
"""Verify StubHub--11.

Sign in as alice.j@test.com (TestPass123!). Report the payment cards currently on file with brand, last four digits, expiry month and year, and which one is the default. Add a new Mastercard test card in Alice's name with a future expiry and three-digit code, make it the default, then remove one of the older non-default cards. Report the final card list with the new default marked.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--11"

from verify_lib import table_diff


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_payments_before", r"/secure/myaccount/payments")
    check_visited_path(judge, traj, "added_card_post", r"/secure/myaccount/payments")
    
    added, removed, changed = table_diff(initial_db, after_db, "payment_cards")
    judge.check("card_delta_shape", len(added) == 1 and len(removed) == 1)
    for row in added.values():
        judge.check("new_card_row", row["user_id"] == 1 and row["brand"] == "Mastercard"
                    and row["holder"] == "Alice Johnson" and row["is_default"] == 1
                    and (row["exp_year"], row["exp_month"]) > (2026, 9))
        judge.check("new_card_reported", row["last4"] in answer and "default" in answer.casefold())
    for row in removed.values():
        judge.check("removed_card_owned", row["user_id"] == 1)
    for before, after in changed.values():
        judge.check("old_card_preserved", before["user_id"] == 1 and after["is_default"] == 0
                    and {k for k in before if before[k] != after[k]} == {"is_default"})
    rows = after_db.execute("SELECT * FROM payment_cards WHERE user_id=1").fetchall()
    judge.check("single_default", sum(r["is_default"] for r in rows) == 1)
    for row in initial_db.execute("SELECT * FROM payment_cards WHERE user_id=1"):
        judge.check("initial_card_reported_" + row["last4"], row["last4"] in answer)
    for row in rows:
        judge.check("final_card_reported_" + row["last4"], row["last4"] in answer)
    check_only_tables_changed(judge, initial_db, after_db, ("payment_cards",))


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
