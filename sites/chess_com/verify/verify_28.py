"""Deterministic verifier for chess_com task 28; see tasks.jsonl and verify/README.md."""
from refined import check
from verify_lib import run_verifier

def run_checks(judge, traj, initial_db, after_db):
    check(28, judge, traj, initial_db, after_db)

if __name__ == "__main__":
    run_verifier("Chess.com--28", run_checks)
