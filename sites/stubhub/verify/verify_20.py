#!/usr/bin/env python3
"""Verify StubHub--20.

Three Seattle teams appear on the site: the Kraken, the Seahawks, and the Sounders FC. For each performer page, report the follower count and the number of upcoming home events. Then report each team's next home game with opponent, date, and get-in price. Which team has the most home events, and which has the largest follower count?
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--20"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_kraken", r"/seattle-kraken-tickets/performer/900000460")
    check_visited_path(judge, traj, "visited_seahawks", r"/seattle-seahawks-tickets/performer/1945")
    check_visited_path(judge, traj, "visited_sounders", r"/seattle-sounders-fc-tickets/performer/388488")
    
    check_answer_number(judge, answer, "kraken_followers", "44,200")
    check_answer_number(judge, answer, "kraken_home_events", 41)
    check_answer_number(judge, answer, "seahawks_followers", "62,800")
    check_answer_number(judge, answer, "seahawks_home_events", 8)
    check_answer_number(judge, answer, "sounders_followers", "56,600")
    check_answer_number(judge, answer, "sounders_home_events", 5)
    check_answer_phrase(judge, answer, "kraken_next", "Calgary Flames")
    check_answer_number(judge, answer, "kraken_next_getin", 65)
    check_answer_phrase(judge, answer, "seahawks_next", "Los Angeles Chargers")
    check_answer_number(judge, answer, "seahawks_next_getin", 236)
    check_answer_phrase(judge, answer, "sounders_next", "Minnesota United")
    check_answer_number(judge, answer, "sounders_next_getin", 18)
    judge.check("most_home_events_verdict",
                "kraken" in answer.casefold() and "most" in answer.casefold(),
                "answer must state the Kraken have the most home events")
    judge.check("largest_followers_verdict",
                "seahawks" in answer.casefold() and ("largest" in answer.casefold()
                                                      or "most" in answer.casefold()),
                "answer must state the Seahawks have the largest follower count")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
