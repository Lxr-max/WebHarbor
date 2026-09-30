#!/usr/bin/env python3
"""Verify Speedo--4.

David (david.k@test.com / TestPass123!) wants to chase his recent Fastskin
order. Sign in, find his most recent order containing a jammer, and report its
order number, status, tracking number and the card charged. Then use the
contact form (category Orders & Delivery, sub-category Where is my order,
quoting the order number) to ask for an update, and report the case reference
you receive.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--4"

ORDER = "SP100007"          # David's only order (Men's Fastskin LZR Pure Valor 2.0 Jammer)
STATUS = "Dispatched"
TRACKING = "SDRM100522663GB"
CARD = "Visa"
LAST4 = "9902"
CASE = "CAS100001"


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_account", r"/account")
    check_visited_path(judge, traj, "visited_order_detail", r"/account/orders/SP100007")
    check_visited_path(judge, traj, "visited_contact", r"/pages/contact")
    check_answer_phrase(judge, answer, "mentions_order", ORDER)
    check_answer_phrase(judge, answer, "mentions_status", STATUS)
    check_answer_phrase(judge, answer, "mentions_tracking", TRACKING)
    check_answer_phrase(judge, answer, "mentions_card", LAST4)
    check_answer_phrase(judge, answer, "mentions_case", CASE)

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"contact_messages"})
    added, removed, _ = table_diff(initial_db, after_db, "contact_messages")
    judge.check("one_case_added", len(added) == 1 and len(removed) == 0,
                f"added={list(added.values())!r}")
    if added:
        row = list(added.values())[0]
        judge.check("case_ref", row["case_ref"] == CASE, f"case_ref={row['case_ref']!r}")
        judge.check("case_category", row["category"] == "Orders & Delivery",
                    f"category={row['category']!r}")
        judge.check("case_subcategory", row["subcategory"] == "Where is my order",
                    f"subcategory={row['subcategory']!r}")
        judge.check("case_quotes_order", row["order_number"] == ORDER,
                    f"order_number={row['order_number']!r}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
