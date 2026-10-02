#!/usr/bin/env python3
"""Verify StubHub--17.

Open Metallica's October 1 Las Vegas event page. Report every event shown in the nearby events section with its date and venue. Then open each nearby event and report its get-in price and total listing count. Which nearby date has the cheapest get-in, and how does the single-night get-in compare with the two-day pass covering the same venue?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--17"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_oct1_single", r"/metallica-las-vegas-tickets-10-1-2026/event/160569378")
    check_visited_path(judge, traj, "visited_nearby_pass", r"/metallica-las-vegas-tickets-10-1-2026/event/160572545")
    check_visited_path(judge, traj, "visited_nearby_oct3", r"/metallica-las-vegas-tickets-10-3-2026/event/160569380")
    check_visited_path(judge, traj, "visited_nearby_pass2", r"/metallica-las-vegas-tickets-10-8-2026/event/160611325")
    check_visited_path(judge, traj, "visited_nearby_oct8", r"/metallica-las-vegas-tickets-10-8-2026/event/160611244")
    
    check_answer_number(judge, answer, "single_night_getin", 749)
    for label, getin, count in (("pass_1_3", 1137, 29), ("oct3", 1124, 10),
                                ("pass_8_10", 1092, 27), ("oct8", 725, 25)):
        check_answer_number(judge, answer, f"nearby_getin_{label}", getin)
        check_answer_number(judge, answer, f"nearby_count_{label}", count)
    judge.check("cheapest_nearby_verdict",
                "725" in answer and ("Oct 8" in answer or "October 8" in answer or "8" in answer),
                "answer must name the Oct 8 single night as the cheapest nearby get-in ($725)")
    # audit fix (2026-09-26): accept the price as displayed on the page
    # ("$1,137" comma form) as well as the plain "1137" form.
    judge.check("pass_comparison",
                ("1137" in answer or "1,137" in answer) and "749" in answer,
                "answer must compare the single-night get-in ($749) with the two-day pass ($1,137)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
