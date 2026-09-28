#!/usr/bin/env python3
"""verify_15.py — deterministic verifier for task REMAX--15.

Fed rate announcement facts, HomeHQ newsletter signup from the front page
with the email and buyer type given in the task.

Ground truth below is HARDCODED (frozen against the shipped seed DB); it never
appears in tasks.jsonl. Navigation gates encode the honest on-site path the
task text implies; a correct answer without that navigation is a shortcut and
fails. See verify_lib.py for the shared contract.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (  # noqa: E402
    Judge, added_rows, check_only_tables_changed, check_seed_contract,
    check_trajectory_identity, contains_amount, contains_any_phrase,
    contains_count, contains_phrase, entered_identity, final_answer,
    nav_article, nav_srp, run_verifier)

TASK_ID = "REMAX--15"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    # Read the Fed article and fill the newsletter form.
    judge.check("nav_article_fed",
                nav_article(traj, "interest-rate-announcement"),
                "required: /advice/interest-rate-announcement")
    judge.check("entered_newsletter_email",
                entered_identity(traj, "rate.watcher@example.com"),
                "required: newsletter form filled with rate.watcher@example.com")
    # ground truth (frozen seed): the Fed raised the federal funds rate to a
    # 3.75% to 4% target range by a 12-0 vote at its September 15-16, 2026
    # meeting.
    judge.check("answer_decision",
                contains_any_phrase(answer, ["raising the federal funds rate",
                                            "raised the federal funds rate",
                                            "hike in the federal funds rate",
                                            "hiked the federal funds rate",
                                            "increase in the federal funds rate",
                                            "increased the federal funds rate",
                                            "raised rates", "increased rates", "hiked rates"]),
                "must state the Fed raised the federal funds rate")
    judge.check("answer_target_range", contains_any_phrase(answer, ["3.75% to 4%", "3.75%-4%", "3.75-4%", "3.75 to 4 percent"]),
                "must quote the 3.75% to 4% target range")
    judge.check("answer_vote", contains_any_phrase(answer, ["12-0", "12 to 0", "12 in favor and none against"]),
                "must state the 12-0 vote")
    judge.check("answer_meeting_dates",
                contains_any_phrase(answer, ["September 15-16, 2026", "September 15 and 16, 2026", "September 15 to 16, 2026", "September 15-16 2026"]),
                "must state the September 15-16, 2026 meeting dates")
    judge.check("answer_newsletter_confirmation",
                contains_any_phrase(answer, ["subscribing", "subscribed",
                                             "thanks for subscribing", "homehq"]),
                "must report the newsletter confirmation")
    # DB after-state: exactly one newsletter subscriber row
    check_seed_contract(judge, initial_db)
    check_only_tables_changed(judge, initial_db, after_db,
                              ["newsletter_subscribers"])
    new_sub = added_rows(after_db, initial_db, "newsletter_subscribers", "id")
    judge.check("exactly_one_new_subscriber", len(new_sub) == 1,
                f"new subscribers: {new_sub}")
    if new_sub:
        r = new_sub[0]
        judge.check("subscriber_email",
                   (r["email"] or "").lower() == "rate.watcher@example.com",
                    f"email={r['email']}")
        judge.check("subscriber_buyer_type",
                   (r["buyer_type"] or "").lower() == "move-up buyer",
                    f"buyer_type={r['buyer_type']}")


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
