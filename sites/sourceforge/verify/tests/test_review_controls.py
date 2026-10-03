"""Targeted synthetic grading controls; these are not browser runs."""
import json,sqlite3
from _support import honest_run,run_verifier

def answer(run,fn):
    p=run/'trajectory.json';t=json.loads(p.read_text());t['final_answer']=fn(t['final_answer']);p.write_text(json.dumps(t))

def test_swapped_project_counts_rejected(tmp_path):
    run=honest_run(tmp_path,0)
    answer(run,lambda a:a.replace('3,600,000','SWAP').replace('768,800','3,600,000').replace('SWAP','768,800'))
    run_verifier(0,run,False)

def test_plain_number_punctuation_accepted(tmp_path):
    run=honest_run(tmp_path,16)
    answer(run,lambda a:a.replace('23,345','23345').replace('1,210','1210'))
    run_verifier(16,run,True)

def test_other_account_preserved(tmp_path):
    run=honest_run(tmp_path,13)
    with sqlite3.connect(run/'after.db') as c:c.execute("UPDATE users SET display_name='Unrequested' WHERE username='alice_j'")
    run_verifier(13,run,False)


def test_natural_vendor_listing_description_accepted(tmp_path):
    run=honest_run(tmp_path,19)
    answer(run,lambda a:a.replace('list your product in the Business Software directory',"a listing in SourceForge's Business Software directory"))
    run_verifier(19,run,True)


def test_games_missing_operating_system_rejected(tmp_path):
    run=honest_run(tmp_path,9)
    answer(run,lambda a:a.replace('Linux','Windows'))
    run_verifier(9,run,False)
