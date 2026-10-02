#!/usr/bin/env python3
"""verify_6.py — deterministic verifier for task REMAX--6.

Illinois-licensed agents (open each profile; most experienced one's name,
title, years, civic activity).

Ground truth below is HARDCODED (frozen against the shipped seed DB); it never
appears in tasks.jsonl. Navigation gates encode the honest on-site path the
task text implies; a correct answer without that navigation is a shortcut and
fails. See verify_lib.py for the shared contract.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_lib import (  # noqa: E402
    Judge, check_read_only, check_trajectory_identity, contains_any_phrase,
    contains_count, contains_phrase, final_answer, nav_agent_detail,
    nav_agents_filtered, run_verifier)

TASK_ID = "REMAX--6"


def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    # Inspect the Illinois directory and profiles.
    judge.check("nav_agents_illinois",
                nav_agents_filtered(traj, licensed="IL"),
                "required: /real-estate-agents with licensed=IL")
    for rid, name in (("100041617", "Ramina Padron"),
                      ("102250128", "Sarah Camargo"),
                      ("100011926", "Scott Eoff")):
        judge.check(f"nav_agent_{rid}", nav_agent_detail(traj, rid),
                    f"required: agent detail for {name} ({rid})")
    # ground truth (frozen seed): IL — Scott Eoff, Managing Broker, 24 years,
    # civic Chamber of Commerce
    judge.check("answer_il_name", contains_phrase(answer, "Scott Eoff"),
                "must name Scott Eoff")
    judge.check("answer_il_title", contains_phrase(answer, "Managing Broker"),
                "must state the Managing Broker title")
    judge.check("answer_il_years", contains_count(answer, 24),
                "must state Scott Eoff's 24 years")
    judge.check("answer_il_civic",
                contains_any_phrase(answer, ["Chamber of Commerce",
                                              "Eagles/Elks/Moose",
                                              "Fraternity/Sorority"]),
                "must name one civic activity from the profile")
    check_read_only(judge, initial_db, after_db)


if __name__ == "__main__":
    run_verifier(TASK_ID, run_checks)
