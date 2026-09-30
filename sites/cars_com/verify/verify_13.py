#!/usr/bin/env python3
"""Deterministic verifier for cars_com task Cars.com--13.

Create a new account (agent-chosen details); search certified pre-owned SUVs
within 100 miles; save the first two listings; save the search with a name and
daily alerts; open the garage and report the two saved cars + the saved
search; remove one saved car and report which remains. Stateful (new user,
2 saved cars -> 1 after the remove, 1 daily saved search).

NOTE: the ground truth assumes the SERP filter-form fix (the review found the
filter form returning 0 results for every real submission)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_lib import (Judge, run_verifier, final_answer, navigated_to,
                        contains_int, contains_price, contains_all,
                        contains_any, check_trajectory_identity,
                        check_signed_in_as, db_query, new_users,
                        saved_car_ids, saved_searches_for, changed_tables)

TASK_ID = "Cars.com--13"
FIRST_CPO_SUV = "270d9740-131d-42f0-b0db-6ab553aa1838"    # 2023 BMW iX xDrive50
SECOND_CPO_SUV = "58c85341-ee72-468a-9a6f-a5640fd4cd5f"   # 2025 Chevrolet Blazer LT


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)

    judge.check("nav_register", navigated_to(traj, "/authn/register"),
                "required: the registration page")
    typed = " ".join(__import__("verify_lib").input_texts(traj))
    judge.check("entered_own_details",
                any("@" in t for t in typed.split()),
                "expected the agent to enter its own account details")
    judge.check("nav_srp", navigated_to(traj, "/shopping/results/"),
                "required: the certified-SUV SERP")
    judge.check("nav_garage", navigated_to(traj, "/profile/your-garage/"),
                "required: the garage page")

    # count: 32 certified SUVs within 100 miles
    judge.check("answer_count", contains_int(answer, 32),
                "expected 32 results")

    # the two saved cars: BMW iX xDrive50 $43,663 + Chevrolet Blazer LT $27,133
    judge.check("answer_saved_two",
                contains_all(answer, ["BMW iX"]) and contains_price(answer, 43663)
                and contains_all(answer, ["Blazer"]) and contains_price(answer, 27133),
                "expected the two saved cars (BMW iX $43,663, Blazer $27,133)")
    # after removing one, exactly one remains
    judge.check("answer_one_remains",
                contains_any(answer, ["remains", "remaining", "left", "still"]),
                "expected the report of which one car remains")

    # DB: a new non-benchmark user exists with exactly 1 saved car (one of the
    # two first CPO SUVs) and 1 saved search with daily alerts
    users = new_users(initial_db, after_db)
    judge.check("new_user_registered", len(users) == 1,
                f"new_users={[u['email'] for u in users]!r}")
    if not users:
        return
    email = users[0]["email"]
    ids = saved_car_ids(after_db, email)
    judge.check("one_saved_car_remains", len(ids) == 1,
                f"saved_cars={[i[:8] for i in ids]!r}")
    judge.check("remaining_is_first_two",
                ids[0] in (FIRST_CPO_SUV, SECOND_CPO_SUV),
                f"remaining={ids[0][:8]!r}")
    searches = saved_searches_for(after_db, email)
    judge.check("one_daily_search",
                len(searches) == 1 and searches[0]["alert_frequency"] == "daily",
                f"searches={[(s['name'], s['alert_frequency']) for s in searches]!r}")
    changed = changed_tables(initial_db, after_db)
    judge.check("only_expected_tables_changed",
                set(changed) <= {"users", "saved_cars", "saved_searches"},
                f"changed_tables={changed!r}")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
