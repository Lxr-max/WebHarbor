#!/usr/bin/env python3
"""Verify The Weather Network--14 (register account + save three locations).

Stateful contract: exactly one new user row (username weather_fan2026) and
exactly three saved_locations rows for that user: Toronto, one ski-channel
location, and one further location of the agent's choice (the vacation
destination). Nothing else may change.
"""
from verify_lib import (check_answer_count_at_least, check_only_tables_changed,
                        check_trajectory_identity, check_user_created,
                        check_visited_path, final_answer, run_verifier,
                        table_diff)

TASK_ID = "The Weather Network--14"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_register", r"/en/account/register")
    check_visited_path(judge, traj, "visited_account", r"/en/account$")
    check_only_tables_changed(judge, initial_db, after_db, {"users", "saved_locations"})
    uid = check_user_created(judge, initial_db, after_db, "weather_fan2026")
    if uid is None:
        return
    a_add, a_rem, a_chg = table_diff(initial_db, after_db, "saved_locations")
    adds = list(a_add.values())
    judge.check("saved_three_added",
               not a_rem and not a_chg and len(adds) == 3
               and all(r["user_id"] == uid for r in adds),
               f"expected exactly 3 saved_locations for uid {uid}; got "
               f"adds={[(r['user_id'], r['loc_id']) for r in adds]} rem={len(a_rem)} chg={len(a_chg)}")
    if len(adds) == 3:
        loc_ids = [r["loc_id"] for r in adds]
        q = ",".join("?" * len(loc_ids))
        locs = {row["id"]: row for row in initial_db.execute(
            f"SELECT id, name, channel, country FROM locations WHERE id IN ({q})",
            loc_ids)}
        names = [locs[i]["name"] for i in loc_ids if i in locs]
        judge.check("saved_includes_toronto",
                    any(locs[i]["name"] == "Toronto" for i in loc_ids if i in locs),
                    f"saved locations must include Toronto; got {names}")
        judge.check("saved_includes_ski",
                    any(locs[i]["channel"] == "ski" for i in loc_ids if i in locs),
                    f"saved locations must include a ski resort; got {names}")
        check_answer_count_at_least(judge, answer, "answer_names_three",
                                    names, 3, label="the three saved location names")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
