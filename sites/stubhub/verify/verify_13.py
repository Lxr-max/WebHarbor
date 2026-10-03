#!/usr/bin/env python3
"""Verify StubHub--13.

The Seattle Kraken's home schedule lists every regular-season game at their home arena. Report the first and last home games with opponent, date, and get-in price. List the next three home games after the opener with dates and opponents. Report the venue's full name and city, and the total number of Kraken home games listed on the site.
"""
from verify_lib import (Judge, check_answer_any, check_answer_number, check_answer_phrase,
                        check_answer_regex, check_answer_one_of, check_read_only,
                        check_only_tables_changed, check_table_deltas, check_trajectory_identity,
                        check_visited_path, final_answer, run_verifier)

TASK_ID = "StubHub--13"



def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_kraken_page", r"/seattle-kraken-tickets/performer/900000460")
    check_visited_path(judge, traj, "paginated_to_last_page", r"/seattle-kraken-tickets/performer/900000460\?page=3")
    
    check_answer_number(judge, answer, "total_home_games", 41)
    check_answer_phrase(judge, answer, "venue_name", "Climate Pledge Arena")
    check_answer_phrase(judge, answer, "venue_city", "Seattle")
    check_answer_phrase(judge, answer, "first_opponent", "Calgary Flames")
    check_answer_number(judge, answer, "first_getin", 65)
    check_answer_phrase(judge, answer, "last_opponent", "Winnipeg Jets")
    check_answer_number(judge, answer, "last_getin", 90)
    for opp in ("Vegas Golden Knights", "Detroit Red Wings", "Utah Mammoth"):
        check_answer_phrase(judge, answer, f"next_three_{opp.split()[0].lower()}", opp)
    from ticket_comparisons import check_endpoints
    check_endpoints(judge, traj, initial_db)
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
