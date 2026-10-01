"""Targeted synthetic grading controls; these are not browser runs."""
import json,sqlite3
from _support import honest_run,run_verifier

def answer(run,fn):
    p=run/'trajectory.json';t=json.loads(p.read_text());t['final_answer']=fn(t['final_answer']);p.write_text(json.dumps(t))

def test_swapped_event_prices_rejected(tmp_path):
    run=honest_run(tmp_path,2)
    answer(run,lambda a:a.replace('$749','SWAP').replace('$1124','$749').replace('SWAP','$1124'))
    run_verifier(2,run,False)

def test_wrong_half_price_rejected(tmp_path):
    run=honest_run(tmp_path,2);answer(run,lambda a:a.replace('$568.50','$568.99'))
    run_verifier(2,run,False)

def test_gift_code_must_match_saved(tmp_path):
    run=honest_run(tmp_path,5)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE gift_card_orders SET code='SHXXXXXXXXXX' WHERE id=5")
    run_verifier(5,run,False)

def test_existing_order_preserved(tmp_path):
    run=honest_run(tmp_path,12)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE orders SET status='Cancelled' WHERE id=1")
    run_verifier(12,run,False)

def test_equivalent_new_mastercard_accepted(tmp_path):
    run=honest_run(tmp_path,11)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE payment_cards SET last4='5556' WHERE id=8")
    answer(run,lambda a:a.replace('4444','5556'))
    run_verifier(11,run,True)


def test_explore_swapped_prices_rejected(tmp_path):
    run=honest_run(tmp_path,18)
    answer(run,lambda a:a.replace('$106','SWAP').replace('$228','$106').replace('SWAP','$228'))
    run_verifier(18,run,False)

def test_explore_missing_venue_rejected(tmp_path):
    run=honest_run(tmp_path,18)
    answer(run,lambda a:a.replace('Sony Hall','Unknown Hall'))
    run_verifier(18,run,False)


def test_team_comparison_without_suggestion_errand_accepted(tmp_path):
    run=honest_run(tmp_path,7)
    answer(run,lambda a:a[a.index('Seattle Sounders FC:'):])
    run_verifier(7,run,True)
