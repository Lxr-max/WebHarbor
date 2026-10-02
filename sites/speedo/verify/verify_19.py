#!/usr/bin/env python3
"""Verify Speedo--19: David's old Visa has been replaced by his club card. Sign in as david.k@test.com (password TestPass123!), remove the existing Visa and save a new default Visa labelled Club, number 4012888812345678, expiring 03/29. Confirm how many cards remain and identify the default by its label, last four digits and expiry, leaving the rest of his account unchanged."""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--19"

DAVID_ID = 4
CARD_ID = 5                 # David's only card row (Sqlite reuses the rowid after delete+add)
NEW_LAST4 = "5678"
NEW_LABEL = "Club"
NEW_EXP = (3, 29)
GOGGLES_IDS = {61, 816}     # Adult Fastskin Speed Socket 2.0 Mirrored Goggles Red/Smoke,
                           # Speedo iQ Vanquisher 3.0 Track Navy


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_payment", r"/account/payment")
    check_answer_number(judge, answer, "card_count", 1, "cards saved")
    check_answer_phrase(judge, answer, "mentions_default", "5678")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"payment_cards"})
    before_others = [tuple(r) for r in initial_db.execute("SELECT * FROM payment_cards WHERE user_id != ? ORDER BY id", (DAVID_ID,))]
    after_others = [tuple(r) for r in after_db.execute("SELECT * FROM payment_cards WHERE user_id != ? ORDER BY id", (DAVID_ID,))]
    judge.check("other_cards_preserved", before_others == after_others)
    rows = after_db.execute("SELECT * FROM payment_cards WHERE user_id = ?", (DAVID_ID,)).fetchall()
    judge.check("one_default_club_card", len(rows) == 1 and all(
        rows[0][k] == v for k, v in {"brand":"Visa", "last4":NEW_LAST4, "label":NEW_LABEL,
                                    "exp_month":3, "exp_year":29, "is_default":1}.items()))
    check_answer_phrase(judge, answer, "card_label", "Club")
    check_answer_phrase(judge, answer, "card_expiry", "03/29")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
