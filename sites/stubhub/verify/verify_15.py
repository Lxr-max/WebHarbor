#!/usr/bin/env python3
"""Verify StubHub--15.

Open the cheapest 4-ticket listing for the October 4 Chargers at Seahawks game. Report its section, row, seat features, zone, and whether a seat view photo appears. Then report its price breakdown at quantity 2 and at quantity 4: per-ticket price, subtotal, and final total including the processing fee. Does the processing fee change with quantity, and what is the per-ticket total at each quantity?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--15"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_chargers_event", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504")
    check_visited_path(judge, traj, "qty4_filter", r"/event/160436504\?[^ ]*quantity=4")
    check_visited_path(judge, traj, "visited_listing_detail", r"/event/160436504/listing/\d+")
    
    check_answer_phrase(judge, answer, "listing_section", "Upper 300-Level")
    check_answer_number(judge, answer, "listing_price", 265)
    check_answer_phrase(judge, answer, "listing_features_clearview", "Clear view")
    judge.check("seat_view_photo_answered",
                "seat view" in answer.casefold(),
                "answer must state whether a seat view photo appears")
    check_answer_number(judge, answer, "subtotal_qty2", 530)
    check_answer_number(judge, answer, "total_qty2", "532.95")
    check_answer_number(judge, answer, "subtotal_qty4", 1060)
    check_answer_number(judge, answer, "total_qty4", "1062.95")
    judge.check("processing_fee_verdict",
                ("does not change" in answer.casefold() or "doesn't change" in answer.casefold()
                 or "same" in answer.casefold()),
                "answer must state the processing fee does not change with quantity")
    check_answer_number(judge, answer, "per_ticket_qty2", "266.48")
    check_answer_number(judge, answer, "per_ticket_qty4", "265.74")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
