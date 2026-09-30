#!/usr/bin/env python3
"""Verify Ticketmaster--5.

I'll be in Las Vegas over the last weekend of October 2026 (October 29 through November 1) and want to catch a concert while I'm there. Compare the Music events in that window by their Standard Admission prices and report the one with the cheapest Standard Admission tickets: its name and date, its cheapest section and row, and the all-in total for 2. Also tell me which day of the week each show falls on.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (Judge, check_answer_any, check_answer_money,
                        check_answer_number, check_answer_phrase,
                        check_input_action, check_only_tables_changed,
                        check_purchase_order, check_read_only,
                        check_row_added, check_row_removed,
                        check_trajectory_identity, check_visited_path,
                        final_answer, run_verifier)

TASK_ID = "Ticketmaster--5"


# Frozen ground truth (reviewer r2 honest walk 2026-09-27, seed md5
# b03a154d...): the Oct 29 - Nov 1 2026 Las Vegas Music window holds two
# Metallica: Life Burns Faster shows at Sphere. Comparing them by Standard
# Admission prices: Oct 29 (event 170064550781E861) cheapest Standard is
# BALC K $134.85 ($269.70 for 2); Oct 31 (event 170064550781E865) cheapest
# Standard is BALC I $132.78 ($265.56 for 2) - the winner. Weekdays:
# Oct 29 is a Thursday, Oct 31 is a Saturday. The display sort (lowest
# starting price, which includes accessible seats) cannot decide this; the
# task pins Standard Admission.
OCT29_EVENT = "170064550781E861"
OCT31_EVENT = "170064550781E865"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_visited_path(judge, traj, "discover with Las Vegas + date window filter",
                       r"/discover/concerts\?.*city=Las")
    urls = [str(u) for u in
            ([traj.get("start_url")] if traj.get("start_url") else [])
            + [s.get("url", "") for s in traj.get("steps") or []]
            + [s.get("url_after", "") for s in traj.get("steps") or []]
            + ([traj.get("final_url")] if traj.get("final_url") else [])]
    metallica_events = sorted({u.split("/event/")[1].split("?")[0]
                               for u in urls if "/event/" in u})
    if {OCT29_EVENT, OCT31_EVENT} <= set(metallica_events):
        judge.evidence(f"compared both window events by Standard Admission: "
                      f"{metallica_events}")
    else:
        judge.fail("did not open both Music events in the window to compare "
                   f"their Standard Admission prices (need {OCT29_EVENT} and "
                   f"{OCT31_EVENT})")
    check_answer_phrase(judge, answer, "event name", "Metallica")
    check_answer_any(judge, answer, "winner date",
                     ["Oct 31", "October 31", "10-31", "10/31", "Oct. 31"])
    check_answer_phrase(judge, answer, "cheapest Standard section", "BALC")
    check_answer_phrase(judge, answer, "cheapest Standard row", "Row I")
    check_answer_money(judge, answer, "all-in total for 2", 265.56)
    ok_weekdays = ("Thursday" in answer and "Saturday" in answer) \
        or ("Thu" in answer and "Sat" in answer)
    if ok_weekdays:
        judge.evidence("answer reports the weekday of each window show "
                      "(Thursday Oct 29 / Saturday Oct 31)")
    else:
        judge.fail("answer does not report which day of the week each show "
                   "falls on (Thursday Oct 29, Saturday Oct 31)")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    sys.exit(run_verifier(TASK_ID, run_checks))
