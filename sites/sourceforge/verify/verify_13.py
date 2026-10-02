#!/usr/bin/env python3
"""Verify SourceForge--13: Set up my SourceForge contributor identity with username fleet-admin, email fleet-admin@example.com and password LongPass123!. Set Germany as my country and choose a display name, then reopen the account page and confirm the saved username, display name and country."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier,
                        table_diff, check_answer_any)

TASK_ID = "SourceForge--13"



def _pid(db, shortname):
    return db.execute("SELECT id FROM projects WHERE shortname = ?", (shortname,)).fetchone()[0]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_registration", r"/user/registration/")
    check_visited_path(judge, traj, "visited_account_edit", r"/account/edit")
    check_visited_path(judge, traj, "visited_account", r"/account/")
    check_answer_phrase(judge, answer, "username_registered", 'fleet-admin')
    check_answer_phrase(judge, answer, "country_germany", 'Germany')
    # stateful: fleet-admin registered (country DE, display name set) and
    # bookmarked CrystalDiskInfo.
    check_only_tables_changed(judge, initial_db, after_db, {"users"})
    added, removed, changed = table_diff(initial_db, after_db, "users")
    ok_u = len(added) == 1 and not removed and not changed
    if ok_u:
        row = list(added.values())[0]
        ok_u = (row["username"] == "fleet-admin"
                and row["email"] == "fleet-admin@example.com"
                and row["country"] == "DE"
                and (row["display_name"] or "") != "")
    if ok_u:
        judge.check("display_name_reported", row["display_name"].casefold() in answer.casefold())
    judge.check("user_registered_de_display_name", ok_u,
                f"added={list(added.values())} removed={list(removed.values())} changed={list(changed.values())[:2]}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
