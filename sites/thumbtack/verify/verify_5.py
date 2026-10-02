#!/usr/bin/env python3
"""Verify Thumbtack--5.

Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I've just moved to Kirkland (zip 98033). Update my profile's zip code to 98033 and address to 123 Main St, Kirkland, WA, then find the highest-rated lawn care professional who serves that area and request a quote for a weekly mowing service.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_number,
                        check_answer_phrase, check_input_action,
                        check_new_user, check_only_tables_changed,
                        check_read_only, check_row_updated,
                        check_table_added, check_table_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Thumbtack--5"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…;
# re-frozen 2026-09-27 in review round 2 from a fresh honest walk — the
# round-1 delta wrongly recorded pro 113 (Slc) in match row 27, but the
# app's deterministic seed_matches (rating desc, hires desc, top 5) always
# selects pro 106 (Bh, 5.0/15 hires) over pro 113 (4.8/102) for a fresh
# lawn-care project; pro 106 is the deterministic non-responder. Verified
# against the live review container walk runs/05 (after.db row 27 =
# (27, 6, 106, 0, NULL, NULL, NULL, 0)).)
NEW_ZIP = "98033"
TARGET_PRO = "Slc - Simple Lawn Care"
LAWN_CAT = 5


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "profile edit", r"/account/profile")
    check_visited_path(judge, traj, "lawn care category sorted",
                       r"/k/lawn-care/near-me\?sort=highest_rated")
    check_visited_path(judge, traj, "target pro profile",
                       r"/wa/kirkland/lawn-care/slc-simple-lawn-care/service/230942537935791237")
    check_visited_path(judge, traj, "quote wizard", r"/projects/new\?category=lawn-care")
    check_visited_path(judge, traj, "project page", r"/projects/6")
    check_answer_number(judge, answer, "new zip", "98033", "zip")
    check_answer_phrase(judge, answer, "target pro name", "Simple Lawn Care")
    check_answer_any(judge, answer, "quote requested",
                     ["quote", "estimate", "request"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"users", "projects", "project_matches"})
    check_row_updated(judge, initial_db, after_db, "users", "id = 3",
                      "zip", NEW_ZIP)
    check_table_added(judge, initial_db, after_db, "projects",
                      [(6, 3, LAWN_CAT, NEW_ZIP, None, None, None,
                        "matched", None)])
    check_table_added(judge, initial_db, after_db, "project_matches",
                      [(26, 6, 105, 1, 255, None, None, 0),
                       (27, 6, 106, 0, None, None, None, 0),
                       (28, 6, 112, 1, 407, None, None, 0),
                       (29, 6, 107, 1, 194, None, None, 0),
                       (30, 6, 110, 1, 378, None, None, 0)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
