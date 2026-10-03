"""Targeted synthetic grading controls; these are not browser runs."""
import json,sqlite3
from _support import honest_run,run_verifier

def answer(run,fn):
    p=run/'trajectory.json';t=json.loads(p.read_text());t['final_answer']=fn(t['final_answer']);p.write_text(json.dumps(t))

def test_swapped_garage_ratings_rejected(tmp_path):
    run=honest_run(tmp_path,8)
    answer(run,lambda a:a.replace('3.4','SWAP').replace('4.8','3.4').replace('SWAP','4.8'))
    run_verifier(8,run,False)

def test_other_users_default_preserved(tmp_path):
    run=honest_run(tmp_path,13)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE payment_methods SET is_default=0 WHERE user_id=1")
    run_verifier(13,run,False)

def test_cancelled_new_reservation_rejected(tmp_path):
    run=honest_run(tmp_path,19)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE reservations SET status='cancelled' WHERE id=9")
    run_verifier(19,run,False)
