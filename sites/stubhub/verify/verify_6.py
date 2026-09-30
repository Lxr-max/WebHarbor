#!/usr/bin/env python3
"""Verify StubHub--6.

Sign in as david.k@test.com (TestPass123!). Add Metallica to your favorites from its performer page, and favorite the December 13 Giants at Seahawks game from its event page. Also favorite one of the similar artists suggested on Metallica's page. Then open Favorites and report all three entries, the number of upcoming events listed for each favorited performer, and the total number of favorites shown.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--6"

import re
from verify_lib import table_diff


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_metallica_page", r"/metallica-tickets/performer/8147")
    check_visited_path(judge, traj, "visited_giants_event", r"/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500")
    check_visited_path(judge, traj, "visited_similar_artist", r"/[\w-]+-tickets/performer/(?!8147)")
    check_visited_path(judge, traj, "visited_favorites", r"/favorites")
    
    # audit fix (2026-09-26): david starts with two seeded favorites (katseye,
    # luke bryan), so after adding the three the task names, Favorites shows
    # FIVE entries. The frozen "3" contradicted the rendered page; the exact
    # added-delta check below (three new rows) is the anti-shortcut and stays.
    check_answer_number(judge, answer, "favorites_total", 5)
    check_answer_phrase(judge, answer, "favorite_metallica", "metallica")
    check_answer_phrase(judge, answer, "favorite_giants_game", "Giants")
    judge.check("similar_artist_favorited",
                "olivia rodrigo" in answer.casefold() or "similar" in answer.casefold(),
                "answer must include the favorited similar artist (Olivia Rodrigo, the first "
                "similar-artist card on Metallica's page)")
    added, removed, changed = table_diff(initial_db, after_db, "favorites")
    judge.check("three_favorites_added", len(added) == 3 and not removed,
                f"exactly three new favorite rows: +{list(added)} -{list(removed)}")
    perfs = [r["performer_id"] for r in added.values() if r["performer_id"]]
    events = [r["event_id"] for r in added.values() if r["event_id"]]
    judge.check("favorites_shape",
                393 in perfs and 129 in events and len(perfs) == 2 and len(events) == 1
                and all(r["user_id"] == 4 for r in added.values()),
                f"david must favorite metallica (393), one similar artist, and the Giants game (129): {[(r['performer_id'], r['event_id']) for r in added.values()]}")
    a2, r2, c2 = table_diff(initial_db, after_db, "performers")
    judge.check("follower_bumps",
                (393,) in c2 and all(v[1]["followers"] == v[0]["followers"] + 1 for v in c2.values())
                and len(c2) == 2,
                f"exactly the two favorited performers get +1 follower: {[(k, v[0]['followers'], v[1]['followers']) for k, v in c2.items()]}")
    check_only_tables_changed(judge, initial_db, after_db, ("favorites", "performers"))


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
