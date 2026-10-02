#!/usr/bin/env python3
"""Verify StubHub--0.

Seattle plays eight 2026 home games at Lumen Field. From the Seahawks performer page, visit every home game's ticket page and report each game's opponent and date in schedule order together with its lowest ticket price. Then name the cheapest game overall, report that game's get-in section and row, and state the highest get-in price among the eight games.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--0"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_seahawks_performer", r"/seattle-seahawks-tickets/performer/1945")
    check_visited_path(judge, traj, "visited_game_1_chargers", r"/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504")
    check_visited_path(judge, traj, "visited_game_2_49ers", r"/seattle-seahawks-seattle-tickets-10-11-2026/event/160436498")
    check_visited_path(judge, traj, "visited_game_3_chiefs", r"/seattle-seahawks-seattle-tickets-10-25-2026/event/160436501")
    check_visited_path(judge, traj, "visited_game_4_bears", r"/seattle-seahawks-seattle-tickets-11-2-2026/event/160436503")
    check_visited_path(judge, traj, "visited_game_5_cardinals", r"/seattle-seahawks-seattle-tickets-11-8-2026/event/160436506")
    check_visited_path(judge, traj, "visited_game_6_cowboys", r"/seattle-seahawks-seattle-tickets-12-7-2026/event/160436508")
    check_visited_path(judge, traj, "visited_game_7_giants", r"/seattle-seahawks-seattle-tickets-12-13-2026/event/160436500")
    check_visited_path(judge, traj, "visited_game_8_rams", r"/seattle-seahawks-seattle-tickets-12-25-2026/event/160436502")
    
    games = [("Los Angeles Chargers", 236), ("San Francisco 49ers", 367),
             ("Kansas City Chiefs", 364), ("Chicago Bears", 298),
             ("Arizona Cardinals", 194), ("Dallas Cowboys", 297),
             ("New York Giants", 194), ("Los Angeles Rams", 275)]
    for opp, price in games:
        check_answer_phrase(judge, answer, f"opponent_{opp.split()[0].lower()}_{price}", opp)
        check_answer_number(judge, answer, f"getin_{opp.split()[0].lower()}", price)
    check_answer_number(judge, answer, "cheapest_price", 194)
    # tie at $194: the Cardinals game (get-in 344 Row EE) or the Giants game (300 Row DD)
    judge.check("cheapest_game_named",
                "cardinals" in answer.casefold() or "giants" in answer.casefold(),
                "answer must name the cheapest game (Cardinals or Giants, both $194)")
    judge.check("cheapest_getin_section",
                bool(__import__("re").search(r"344|300", answer)),
                "answer must report the cheapest game's get-in section (344 for Cardinals / 300 for Giants)")
    judge.check("cheapest_getin_row",
                "ee" in answer.casefold().replace(" ", "") or "dd" in answer.casefold().replace(" ", ""),
                "answer must report the cheapest game's get-in row (EE / DD)")
    check_answer_number(judge, answer, "highest_getin", 367)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
