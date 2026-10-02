#!/usr/bin/env python3
"""Verify Statista--6 against the reviewed task and saved browser state."""
from task_specs import SPECS
from verify_lib import apply_spec, run_verifier

TASK_ID = "Statista--6"


def run_checks(judge, traj, initial_db, after_db):
    apply_spec(judge, traj, initial_db, after_db, SPECS[6], TASK_ID)


if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
