"""Compare the first three upcoming catalog events through their ticket pages."""
from verify_lib import check_trajectory_identity, check_read_only, run_verifier
from ticket_comparisons import check_explore
TASK_ID = "StubHub--18"
def run_checks(judge, traj, initial_db, after_db):
    check_trajectory_identity(judge, traj, TASK_ID)
    check_explore(judge, traj, initial_db)
    check_read_only(judge, initial_db, after_db)
if __name__ == "__main__":
    raise SystemExit(run_verifier(TASK_ID, run_checks))
