"""Deterministic verifier for porsche task 14; see tasks.jsonl and verify/README.md."""
import json
from pathlib import Path
from verify_lib import *
ENTITIES = json.loads(Path(__file__).with_name('dealer_comparison.json').read_text())
def run_checks(judge, traj, initial_db, after_db):
    check_trajectory_identity(judge, traj, 'Porsche--14')
    check_seed_contract(judge, initial_db)
    answer = final_answer(traj)
    for e in ENTITIES:
        judge.check(e['dealer']+' detail', navigated_vehicle_detail(traj, e['slug']))
        judge.check(e['dealer']+' facts', all(contains_phrase(answer, x) for x in [e['dealer'],e['name'],e['vin'],e['hours']]) and contains_amount(answer,e['price']))
    judge.check('dealer_hours', navigated_dealer_search(traj))
    check_read_only(judge,initial_db,after_db)
if __name__ == '__main__':
    run_verifier('Porsche--14',run_checks)
