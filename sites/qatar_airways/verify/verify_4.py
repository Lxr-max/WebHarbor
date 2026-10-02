"""Compare two Australian arrival options against a local pickup deadline."""
import re
from verify_lib import check_trajectory_identity, check_seed_identity, check_read_only, navigated_flight_status, contains_all, contains_time, final_answer, run_verifier
TASK_ID = "Qatar Airways--4"
def run_checks(judge, traj, initial_db, after_db):
    answer = final_answer(traj)
    check_trajectory_identity(judge, traj, TASK_ID)
    check_seed_identity(judge, initial_db)
    for dest, name, flight, dep, arr in [("SYD","Sydney","QR908","20:05","17:10"), ("MEL","Melbourne","QR904","20:20","16:50")]:
        judge.check("visited_"+dest, navigated_flight_status(traj, mode="route", origin="DOH", dest=dest))
        pattern = rf"(?:{name}|{flight})[^;\n]+"
        segments = re.findall(pattern, answer, re.I)
        judge.check("flight_"+dest, any(contains_all(s,[flight,"777-300ER"]) and contains_time(s,dep) and contains_time(s,arr) for s in segments))
    judge.check("recommended_melbourne", bool(re.search(r"(?:recommend|choose|pick|meets)[^.;\n]{0,50}Melbourne|Melbourne[^.;\n]{0,60}(?:meets|before|recommend|choose)", answer, re.I)))
    check_read_only(judge, initial_db, after_db)
if __name__ == "__main__": run_verifier(TASK_ID, run_checks)
