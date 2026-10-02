#!/usr/bin/env python3
"""Verify Speedo--14: Create a Speedo account for Priya Sharma (priya.sharma@example.com, password SwimFast2026!) and start a wishlist for her child's swimming lessons. Compare the in-stock Kids Sunny G goggles and save the cheapest pair. Report which goggles were saved and the wishlist count."""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--14"

EMAIL = "priya.sharma@example.com"
NAME = "Priya Sharma"
PHONE = "+44 7700 900123"
# cheapest in-stock Kids Sunny G goggles: Kids Sunny G Seasiders Goggles White £8.00
GOGGLES_ID = 388
GOGGLES_NAME = "Kids Sunny G Seasiders Goggles White"


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_register", r"/register")
    check_visited_path(judge, traj, "visited_goggles_pdp",
                       r"/products/kids-sunny-g-seasiders-goggles-white")
    check_answer_phrase(judge, answer, "mentions_goggles", "Sunny G")
    check_answer_number(judge, answer, "wishlist_count", 1, "wishlist count")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"users", "wishlist_items"})
    added, removed, _ = table_diff(initial_db, after_db, "users")
    judge.check("one_user_added", len(added) == 1 and len(removed) == 0,
                f"added={list(added.values())!r}")
    if added:
        row = list(added.values())[0]
        judge.check("user_row", row["email"] == EMAIL and row["name"] == NAME,
                    f"row={dict(row)}")
    import bcrypt
    try:
        password_ok = len(added) == 1 and bcrypt.checkpw(b"SwimFast2026!", next(iter(added.values()))["password_hash"].encode())
    except ValueError:
        password_ok = False
    judge.check("new_password", password_ok)
    a, r, _ = table_diff(initial_db, after_db, "wishlist_items")
    judge.check("one_wishlist_row",
                len(a) == 1 and len(r) == 0
                and list(a.values())[0]["product_id"] == GOGGLES_ID
                and len(added) == 1 and list(a.values())[0]["user_id"] == list(added.values())[0]["id"],
                f"added={list(a.values())!r}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
