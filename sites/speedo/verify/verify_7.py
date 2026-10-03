#!/usr/bin/env python3
"""Verify Speedo--7.

Carol (carol.d@test.com / TestPass123!) has moved to the coast. Sign in, update
her profile phone number to +44 1632 960111, add a new default address (Home,
3 Cliffside Road, Newquay, TR7 1AA), and remove the old Plymouth address.
Report how many addresses are saved and which one is the default.
"""
from verify_lib import (Judge, check_answer_number, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "Speedo--7"

CAROL_ID = 3
PHONE = "+44 1632 960111"
NEW_LINE1 = "3 Cliffside Road"
NEW_CITY = "Newquay"
NEW_POSTCODE = "TR7 1AA"
OLD_CITY = "Plymouth"


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_login", r"/login")
    check_visited_path(judge, traj, "visited_profile", r"/account/profile")
    check_visited_path(judge, traj, "visited_addresses", r"/account/addresses")
    check_answer_phrase(judge, answer, "mentions_newquay", "Newquay")
    check_answer_number(judge, answer, "address_count", 2, "addresses saved")

    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"users", "addresses"})
    # profile phone updated
    added, removed, changed = table_diff(initial_db, after_db, "users")
    ok_phone = False
    for _, (_before, after) in changed.items():
        if after["id"] == CAROL_ID and after["phone"] == PHONE:
            ok_phone = True
    judge.check("carol_phone_updated",
                ok_phone and not added and not removed,
                f"users added={list(added.values())!r} removed={list(removed.values())!r} "
                f"changed_ids={[c[1]['id'] for c in changed.values()]}")
    # addresses: +1 new default Newquay, -1 Plymouth, old default un-defaulted
    a, r, c = table_diff(initial_db, after_db, "addresses")
    judge.check("address_delta", len(a) == 1 and len(r) == 1 and len(c) == 1,
                f"added={list(a.values())!r} removed={list(r.values())!r} changed={list(c.keys())!r}")
    if a:
        row = list(a.values())[0]
        judge.check("new_address_row",
                    row["user_id"] == CAROL_ID and row["line1"] == NEW_LINE1
                    and row["city"] == NEW_CITY and row["postcode"] == NEW_POSTCODE
                    and row["is_default"] == 1,
                    f"row={dict(row)}")
    if r:
        row = list(r.values())[0]
        judge.check("removed_is_plymouth",
                    row["city"] == OLD_CITY,
                    f"removed row={dict(row)}")
    for _, (before, after) in c.items():
        judge.check("old_default_unflagged",
                    before["is_default"] == 1 and after["is_default"] == 0,
                    f"before={before['is_default']} after={after['is_default']}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
