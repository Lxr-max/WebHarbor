#!/usr/bin/env python3
"""Verify The Weather Network--17 (5-city current-conditions ranking)."""
from verify_lib import (check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--17"

CITIES = [
    ("toronto", r"/en/city/ca/ontario/toronto/current", "18"),
    ("halifax", r"/en/city/ca/nova-scotia/halifax/current", "15"),
    ("charlottetown", r"/en/city/ca/prince-edward-island/charlottetown/current", "12"),
    ("winnipeg", r"/en/city/ca/manitoba/winnipeg/current", "17"),
    ("calgary", r"/en/city/ca/alberta/calgary/current", "6"),
]


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    from reviewed_checks import check_answer
    check_answer(judge, traj, 17)
    check_trajectory_identity(judge, traj, TASK_ID)
    for name, pattern, temp in CITIES:
        check_visited_path(judge, traj, f"visited_{name}", pattern)
        check_answer_number(judge, answer, f"answer_temp_{name}", temp,
                            label=f"{name} current temp")
    # ranking warmest -> coldest: Toronto 18 > Winnipeg 17 > Halifax 15 > Charlottetown 12 > Calgary 6
    order = ["toronto", "winnipeg", "halifax", "charlottetown", "calgary"]
    positions = []
    for city in order:
        idx = answer.casefold().find(city)
        judge.check(f"answer_mentions_{city}", idx >= 0, f"answer must mention {city}")
        positions.append(idx)
    judge.check("answer_ranking_order",
                all(0 <= a < b for a, b in zip(positions, positions[1:]) if a >= 0 and b >= 0),
                f"answer must list the cities warmest->coldest; positions={positions}")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
