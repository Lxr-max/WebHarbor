#!/usr/bin/env python3
"""Verify Thumbtack--18.

Log in with the demo account (email: carol.d@test.com, password: TestPass123!). I need a makeup artist for my October 18 event and would like the one with the most Thumbtack hires. Compare the wedding and event makeup artists and tell me the leader's name, number of hires, and review count. Check their profile for Top Pro status and how fast they respond, message them about availability for an October 18 event, follow up asking about a pre-event trial, then save them to my saved pros. Report both replies.
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

TASK_ID = "Thumbtack--18"

# frozen ground truth (reviewer honest walk 2026-09-27, seed md5 0c1320fd…)
TOP_PRO_NAME = "Mel Mua"
TOP_PRO_PK = 549098172844007430
TOP_HIRES = 121
TOP_REVIEWS = 71
TOP_RESPONSE = "28 min"
TRIAL_REPLY = "love to do your makeup"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "login page", r"/login")
    check_visited_path(judge, traj, "services near me", r"/near-me")
    check_visited_path(judge, traj, "makeup category sorted by hires", r"/k/makeup-artists/near-me\?sort=most_hires")
    check_visited_path(judge, traj, "top pro profile", r"/wa/redmond/makeup-artists/mel-mua/service/549098172844007430")
    check_visited_path(judge, traj, "October 18 message flow", r"/message/549098172844007430|/account/messages/2")
    check_answer_phrase(judge, answer, "top pro name", TOP_PRO_NAME)
    check_answer_number(judge, answer, "top hires", TOP_HIRES, "hire")
    check_answer_number(judge, answer, "top reviews", TOP_REVIEWS, "review")
    check_answer_any(judge, answer, "top pro status", ["top pro"])
    check_answer_phrase(judge, answer, "response speed", TOP_RESPONSE)
    check_answer_phrase(judge, answer, "trial replies", TRIAL_REPLY)
    check_answer_any(judge, answer, "saved", ["saved", "save"])
    check_only_tables_changed(judge, initial_db, after_db,
                              {"saved_pros", "threads", "messages"})
    check_table_added(judge, initial_db, after_db, "saved_pros",
                      [(14, 3, 130, None)])
    check_table_added(judge, initial_db, after_db, "threads",
                      [(2, 3, 130, None, None)])
    check_table_added(judge, initial_db, after_db, "messages",
                      [(3, 2, "user", None, None),
                       (4, 2, "pro", None, None),
                       (5, 2, "user", None, None),
                       (6, 2, "pro", None, None)])


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
