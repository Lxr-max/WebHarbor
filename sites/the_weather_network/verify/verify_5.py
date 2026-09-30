#!/usr/bin/env python3
"""Verify The Weather Network--5 (bob: remove odd, add Whistler, go imperial).

r2 re-sync: the task adds the unit switch. Stateful contract: bob.c@test.com
(uid 2) starts with Vancouver, Victoria, Kelowna (BC) and Banff National
Park - Banff (the odd Alberta park), units metric. After the task he must
have exactly 4 saved locations (three BC entries + Whistler Blackcomb), his
unit preference must be imperial, and the account page must show Whistler
Blackcomb at 52°F.
"""
from verify_lib import (check_answer_number, check_only_tables_changed,
                        check_read_only, check_saved_location_delta,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--5"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 5)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_sign_in", r"/en/account/sign-in")
    check_visited_path(judge, traj, "visited_account", r"/en/account$")
    check_visited_path(judge, traj, "visited_whistler", r"/en/ski/ca/british-columbia/whistler-blackcomb")
    # NOTE: the °F toggle is a redirect-through URL (preferences?unit=imperial bounces
    # back to the referrer), so the unit switch is enforced via the DB delta below and
    # the imperial answer value — not via a URL gate (r1 finding #9 precedent).
    # the count after remove + add: 4
    check_answer_number(judge, answer, "answer_total_saved", "4", label="saved locations total")
    # Whistler Blackcomb current temperature in Fahrenheit on the account page
    check_answer_number(judge, answer, "answer_whistler_f", "52",
                        label="Whistler Blackcomb temperature in °F")
    check_only_tables_changed(judge, initial_db, after_db, {"saved_locations", "users"})
    check_saved_location_delta(judge, initial_db, after_db, "bob.c@test.com",
                               added_path="ca/british-columbia/whistler-blackcomb",
                               removed_path="ca/alberta/banff-national-park-banff",
                               final_count=4)
    # users table: exactly bob's unit preference flipped to imperial, nothing else
    import sqlite3  # noqa: F401  (rows come as sqlite3.Row from the runner)
    before = {r["id"]: dict(r) for r in initial_db.execute("SELECT * FROM users")}
    after = {r["id"]: dict(r) for r in after_db.execute("SELECT * FROM users")}
    same_ids = before.keys() == after.keys()
    changed = [uid for uid in after if uid in before and before[uid] != after[uid]]
    ok = (same_ids and len(changed) == 1 and changed[0] == 2
          and before[2]["unit"] == "metric" and after[2]["unit"] == "imperial"
          and all(before[2][k] == after[2][k] for k in before[2] if k != "unit"))
    judge.check("bob_unit_imperial_only_change", ok,
                f"users table must change only bob's unit metric->imperial; "
                f"changed={changed} bob_after={after.get(2, {}).get('unit')!r}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
