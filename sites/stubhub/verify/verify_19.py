"""Validate a gift purchase against the actual recipient, code and saved history."""
import re
from verify_lib import (check_trajectory_identity, check_visited_path, table_diff,
                        check_only_tables_changed, final_answer, run_verifier)
TASK_ID = "StubHub--19"
def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "gift_page", r"/gift-cards")
    ua, ur, uc = table_diff(initial_db, after_db, "users")
    judge.check("users_preserved", len(ua) == 1 and not ur and not uc)
    uid = next(iter(ua.values()))["id"] if ua else 3
    added, removed, changed = table_diff(initial_db, after_db, "gift_card_orders")
    judge.check("gift_history_preserved", len(added) == 1 and not removed and not changed)
    for row in added.values():
        judge.check("gift_requested", row["user_id"] == uid and row["amount"] == 50 and row["design"] == "sports")
        judge.check("gift_code_matches", bool(re.fullmatch(r"SH[A-Z0-9]{10}", row["code"])) and row["code"] in answer)
        judge.check("gift_status", row["status"] == "Delivered" and "delivered" in answer.casefold())
        judge.check("personal_message", bool((row["message"] or "").strip()))
        judge.check("valid_recipient", bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", row["recipient_email"] or "")))
        judge.check("recipient_reported", row["recipient_email"].casefold() in answer.casefold())
        judge.check("amount_reported", "50" in answer)
    check_only_tables_changed(judge, initial_db, after_db, ("users", "gift_card_orders"))
if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
