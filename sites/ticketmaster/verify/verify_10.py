#!/usr/bin/env python3
"""Verify Ticketmaster--10.

Log in as david.k@test.com with password TestPass123!. I am replacing my Rod Wave concert plan with Trans-Siberian Orchestra. Remove the saved event for the Rod Wave tour, add the Trans-Siberian Orchestra artist page as a favorite, and then report exactly which items remain listed under My Favorites.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_money,
                        check_answer_number, check_answer_phrase,
                        check_input_action, check_only_tables_changed,
                        check_purchase_order, check_read_only,
                        check_row_added, check_row_removed, check_row_swap,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Ticketmaster--10"


# Frozen ground truth: david (user 4) favorites: event "Rod Wave: Don't Look
# Down Tour" (0C0064D2AAFF8050), artist "The Book of Mormon (Touring)"
# (1732682), event "Metallica: Life Burns Faster" (17006455FF50D564). After
# removing the Rod Wave event favorite and adding the Trans-Siberian
# Orchestra artist page (780815) as a favorite, exactly those three remain:
# Book of Mormon (artist), Metallica (event), Trans-Siberian Orchestra
# (artist).
# favorites columns: (id, user_id, artist_id, event_id, created_at)
REMOVED_ROW = (None, 4, None, "0C0064D2AAFF8050", None)
ADDED_ROW = (None, 4, "780815", None, None)


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "signin", r"/signin")
    check_input_action(judge, traj, "demo email", r"david\.k@test\.com")
    check_visited_path(judge, traj, "My Favorites", r"/member/favorites")
    check_visited_path(judge, traj, "the TSO artist page", r"/artist/780815")
    check_answer_phrase(judge, answer, "remaining artist favorite", "Book of Mormon")
    check_answer_phrase(judge, answer, "remaining event favorite", "Metallica")
    check_answer_phrase(judge, answer, "newly added favorite", "Trans-Siberian")
    check_only_tables_changed(judge, initial_db, after_db, {"favorites"})
    check_row_swap(judge, initial_db, after_db, "favorites",
                   ADDED_ROW, REMOVED_ROW,
                   "TSO artist favorite added and Rod Wave event favorite removed")


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
