#!/usr/bin/env python3
"""Verify SoundCloud--19: I want to explore the artist crossing over between this week's US Rock and Folk top tens. Identify the artist and the two tracks, with their chart positions, exact plays and labels. Build a listening shortlist from the artist's three most-played Popular tracks, giving each title and exact play count, and summarize the artist's follower count and uploaded-track count. Check whether either crossover track also appears on the UK Indie chart and report its position."""
from verify_lib import (Judge, check_answer_number, check_answer_phrase, check_read_only,
                        check_trajectory_identity, check_visited_path, final_answer,
                        run_verifier)

TASK_ID = "SoundCloud--19"

ARTIST = "Steve Lacy"
PROFILE_PATH = "/steevlacy"
FOLLOWERS = 377394
TRACKS_UPLOADED = 52
ROCK = ("oh yeah?", 3, 211561, "L-M Records/RCA Records", "/steevlacy/oh-yeah")
FOLK = ("nothing", 6, 85000, "L-M Records/RCA Records", "/steevlacy/nothing")
# Popular tab top three (titles, exact plays, page paths) — the tab rows only
# show compact plays, so each exact count is frozen from its track page.
POP1 = ("Buttons", 1059416, "/steevlacy/buttons")
POP2 = ("oh yeah?", 211561, "/steevlacy/oh-yeah")
POP3 = ("doom", 128218, "/steevlacy/doom")
UK_INDIE = ("oh yeah?", 3)
# UK Indie #1 and its artist's profile follower count (text-bound to the profile).
INDIE1 = ("Guilty", "Sammi Heaney", 33262, "/sam-heaney-433035397/guilty")
INDIE1_PROFILE = "/sam-heaney-433035397"
INDIE1_FOLLOWERS = 118


def run_checks(judge, traj, initial_db, after_db):
    from state_review import check_existing_state
    check_existing_state(judge, initial_db, after_db, TASK_ID)
    answer = final_answer(traj)
    from answer_review import bind_tracks
    bind_tracks(judge, answer, [('Buttons', 1059416, None, None), ('oh yeah?', 211561, None, None), ('doom', 128218, None, None), ('nothing', 85000, None, None)])
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_rock_chart", r"/music-charts-us/sets/rock")
    check_visited_path(judge, traj, "visited_folk_chart", r"/music-charts-us/sets/folk")
    check_visited_path(judge, traj, "visited_rock_track", ROCK[4])
    check_visited_path(judge, traj, "visited_folk_track", FOLK[4])
    check_visited_path(judge, traj, "visited_profile", PROFILE_PATH + r"/?(\?|$)")
    check_visited_path(judge, traj, "visited_popular_tab", PROFILE_PATH + r"\?tab=popular")
    check_visited_path(judge, traj, "visited_pop1_track", POP1[2])
    check_visited_path(judge, traj, "visited_pop3_track", POP3[2])
    check_visited_path(judge, traj, "visited_uk_indie", r"/music-charts-uk/sets/indie")
    check_answer_phrase(judge, answer, "artist_name", ARTIST)
    check_answer_phrase(judge, answer, "rock_title", ROCK[0])
    check_answer_number(judge, answer, "rock_position", ROCK[1], "US Rock chart position")
    check_answer_number(judge, answer, "rock_plays", ROCK[2], "rock track exact plays")
    check_answer_phrase(judge, answer, "rock_label", ROCK[3])
    check_answer_phrase(judge, answer, "folk_title", FOLK[0])
    check_answer_number(judge, answer, "folk_position", FOLK[1], "US Folk chart position")
    check_answer_number(judge, answer, "folk_plays", FOLK[2], "folk track exact plays")
    check_answer_phrase(judge, answer, "folk_label", FOLK[3])
    check_answer_number(judge, answer, "followers", FOLLOWERS, "Steve Lacy exact followers")
    check_answer_number(judge, answer, "tracks_uploaded", TRACKS_UPLOADED,
                        "Steve Lacy tracks uploaded")
    check_answer_phrase(judge, answer, "pop1_title", POP1[0])
    check_answer_number(judge, answer, "pop1_plays", POP1[1], "popular #1 exact plays")
    check_answer_phrase(judge, answer, "pop2_title", POP2[0])
    check_answer_number(judge, answer, "pop2_plays", POP2[1], "popular #2 exact plays")
    check_answer_phrase(judge, answer, "pop3_title", POP3[0])
    check_answer_number(judge, answer, "pop3_plays", POP3[1], "popular #3 exact plays")
    check_answer_phrase(judge, answer, "uk_indie_title", UK_INDIE[0])
    check_answer_number(judge, answer, "uk_indie_position", UK_INDIE[1],
                        "UK Indie chart position")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
