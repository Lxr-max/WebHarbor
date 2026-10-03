#!/usr/bin/env python3
"""Verify The Weather Network--4 (imperial units + 4-city current comparison)."""
from verify_lib import (check_answer_number, check_answer_phrase, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--4"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 4)
    check_trajectory_identity(judge, traj, TASK_ID)
    # NOTE: the °F toggle is a redirect-through URL (/en/account/preferences?unit=imperial
    # bounces straight back to the referrer), so an honest agent's trajectory records the
    # post-redirect URL. The toggle is instead enforced by the imperial answer values
    # (63°F / 16 mph are only rendered after the switch).
    check_visited_path(judge, traj, "visited_vancouver", r"/en/city/ca/british-columbia/vancouver/current")
    check_visited_path(judge, traj, "visited_winnipeg", r"/en/city/ca/manitoba/winnipeg/current")
    check_visited_path(judge, traj, "visited_moncton", r"/en/city/ca/new-brunswick/moncton/current")
    check_visited_path(judge, traj, "visited_calgary", r"/en/city/ca/alberta/calgary/current")
    # warmest: Winnipeg 17°C == 63°F, wind 26 km/h == 16 mph (Light rain)
    check_answer_phrase(judge, answer, "answer_warmest_winnipeg", "winnipeg")
    check_answer_number(judge, answer, "answer_temp_f", "63", label="°F")
    check_answer_number(judge, answer, "answer_wind_mph", "16", label="mph")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
