#!/usr/bin/env python3
"""Verify SoundCloud--7: Help David prepare his producer account for a new release. Sign in as david.k@test.com (password TestPass123!), subscribe to yearly Next Pro with card 4242 4242 4242 4242, and upload 'Night Shift Demo', genre Rock, lasting 4 minutes 12 seconds. Report the subscription price and renewal date, and the uploaded track's page URL."""
from verify_lib import (Judge, check_answer_phrase,
                        check_only_tables_changed, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier, table_diff)

TASK_ID = "SoundCloud--7"

PLAN_CODE = "next-pro"
CYCLE = "yearly"
AMOUNT = 9900
RENEWS = "2027-09-26"
UPLOAD_TITLE = "Night Shift Demo"
UPLOAD_GENRE = "Rock"
UPLOAD_DURATION_MS = 252000          # 4:12
UPLOAD_SLUG = "night-shift-demo"
UPLOAD_PATH = "/david_k/night-shift-demo"


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_signin", r"/signin")
    check_visited_path(judge, traj, "visited_plans", r"/upgrade")
    check_visited_path(judge, traj, "visited_confirmation", r"/upgrade/done")
    check_visited_path(judge, traj, "visited_upload", r"/upload")
    check_visited_path(judge, traj, "visited_new_track_page", UPLOAD_PATH)

    # plans-page comparison facts
    # yearly Next Pro checkout facts
    judge.check("yearly_price", ("$99" in answer) or ("99.00" in answer),
                "answer must report the $99.00 yearly price")
    judge.check("renewal_date",
                ("september 26, 2027" in answer.casefold())
                or ("sept 26 2027" in answer.casefold())
                or ("2027-09-26" in answer) or ("26 september 2027" in answer.casefold()),
                "answer must report the renewal date September 26, 2027")
    # upload facts
    import re as _re
    judge.check("answer_has_upload_url",
                bool(_re.search(r"/david_k/night-shift-demo(?![a-z0-9-])", answer)),
                f"answer must report the new track URL {UPLOAD_PATH} exactly")
    check_answer_phrase(judge, answer, "upload_title", UPLOAD_TITLE)

    # DB after-state: one new subscription row for David + the uploaded track
    # (with its auto-created david_k artist row), and nothing else.
    check_only_tables_changed(judge, initial_db, after_db,
                              allowed={"subscriptions", "tracks", "artists"})
    added, removed, _ = table_diff(initial_db, after_db, "subscriptions")
    judge.check("one_subscription_added", len(added) == 1 and not removed,
                f"added={list(added.values())!r} removed={list(removed.values())!r}")
    if added:
        row = list(added.values())[0]
        judge.check("subscription_row",
                   row["user_id"] == 4 and row["plan_code"] == PLAN_CODE
                   and row["cycle"] == CYCLE and row["amount"] == AMOUNT
                   and str(row["renews_at"]).startswith(RENEWS)
                   and row["card_last4"] == "4242",
                   f"row={dict(row)}")
    added, removed, _ = table_diff(initial_db, after_db, "tracks")
    judge.check("one_track_added", len(added) == 1 and not removed,
                f"added={list(added.values())!r}")
    if added:
        row = list(added.values())[0]
        judge.check("track_row",
                   row["title"] == UPLOAD_TITLE and row["duration"] == UPLOAD_DURATION_MS
                   and (row["genre"] or "") == UPLOAD_GENRE
                   and row["permalink"] == UPLOAD_SLUG and row["plays"] == 0,
                   f"row={dict(row)}")
        artist_id = row["artist_id"]
        a, r, c = table_diff(initial_db, after_db, "artists")
        judge.check("one_artist_added", len(a) == 1 and not r and not c,
                    f"added={list(a.values())!r} changed={list(c)[:2]}")
        if a:
            new_artist = list(a.values())[0]
            judge.check("artist_is_david",
                       new_artist["id"] == artist_id and new_artist["permalink"] == "david_k"
                       and new_artist["track_count"] == 1,
                       f"artist={dict(new_artist)}")


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
