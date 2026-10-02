#!/usr/bin/env python3
"""Verify The Weather Network--12 (three Alberta beaches weekend comparison).

r2 re-sync: re-anchored to three beaches with a unique Saturday verdict.
Frozen ground truth (weekend rows): Saturday — Aspen Beach Provincial Park
on Gull Lake 10°C (warmest, unique), Alberta Beach at Lac Ste. Anne 9°C,
Gregoire Lake Provincial Park Beach 8°C with 90% PoP and ~5 mm rain (the
only rainy beach); the other two stay dry (0 mm). Sunday outlook is
identical at all three: Sunny, 14°C, 10% PoP.
"""
from verify_lib import (check_answer_any, check_answer_number, check_read_only,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "The Weather Network--12"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_visited_path(judge, traj, "visited_alberta_beach_weekend",
                       r"/en/beach/ca/alberta/alberta-beach-at-lac-ste-anne/weekend")
    check_visited_path(judge, traj, "visited_aspen_beach_weekend",
                       r"/en/beach/ca/alberta/aspen-beach-provincial-park-on-gull-lake/weekend")
    check_visited_path(judge, traj, "visited_gregoire_weekend",
                       r"/en/beach/ca/alberta/gregoire-lake-provincial-park-beach/weekend")
    # warmest on Saturday (unique)
    check_answer_any(judge, answer, "answer_warmest_saturday",
                     ["aspen beach", "aspen"],
                     label="warmest beach on Saturday")
    check_answer_number(judge, answer, "answer_warmest_sat_temp", "10",
                        label="Aspen Beach Saturday high")
    # the rainy beach + roughly how much
    check_answer_any(judge, answer, "answer_rainy_beach",
                     ["gregoire"], label="beach expecting rain on Saturday")
    check_answer_any(judge, answer, "answer_rain_amount",
                     ["~5", "5 mm", "about 5", "around 5", "5 millimetres", "5-6"],
                     label="roughly how much rain")
    # the other two stay dry
    check_answer_any(judge, answer, "answer_other_two_dry",
                     ["dry", "no rain", "stay dry", "without rain"],
                     label="other two beaches dry verdict")
    # Sunday outlook shared by all three
    check_answer_any(judge, answer, "answer_sunday_same",
                     ["same", "identical", "all three", "share"],
                     label="Sunday outlook same at all three")
    check_answer_number(judge, answer, "answer_sunday_high", "14",
                        label="shared Sunday high")
    check_answer_any(judge, answer, "answer_sunday_sky", ["sunny"],
                     label="shared Sunday sky")
    check_answer_number(judge, answer, "answer_sunday_pop", "10",
                        label="shared Sunday PoP")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
