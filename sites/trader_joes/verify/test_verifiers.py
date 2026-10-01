"""Portable grading controls; copied fixtures never alter browser evidence.

Set WEBHARBOR_REVIEW_RUNS to a directory containing task-00 through task-19.
"""
from pathlib import Path
import copy, importlib.util, json, os, re, shutil, sqlite3
import pytest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('engine_'+HERE.parent.name,HERE/'contract_engine.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
CONTRACT=json.loads((HERE/'contract.json').read_text());RUNS=os.environ.get('WEBHARBOR_REVIEW_RUNS')

def test_contract_matches_tasks():
    tasks=[json.loads(l) for l in (HERE.parent/'tasks.jsonl').read_text().splitlines()]
    assert set(CONTRACT)=={t['id'] for t in tasks}
    for t in tasks:
        c=CONTRACT[t['id']]
        assert c['task']==t['ques'] and c['paths'] and c['claims']
        for label,pattern in c['claims']:re.compile(pattern)

@pytest.mark.parametrize('task_id',list(CONTRACT))
def test_empty_or_wrong_claims_fail(task_id):
    for text in ['', 'Everything is 999999.99 and nobody saved anything.', 'These claims are false.']:
        with pytest.raises(ValueError):E.check_claims(text,CONTRACT[task_id]['claims'])

@pytest.mark.parametrize('mutation',['add','remove','update'])
def test_preserves_unrelated_rows(mutation):
    before={'rows':{'[1]':{'id':1,'owner':8,'qty':2}}};after=copy.deepcopy(before)
    if mutation=='add':after['rows']['[2]']={'id':2,'owner':8,'qty':2}
    elif mutation=='remove':after['rows'].clear()
    else:after['rows']['[1]']['qty']=9
    with pytest.raises(ValueError):E.check_state(before,after,{'initial_digest':E.digest(before)})

@pytest.mark.skipif(not RUNS,reason='Browser fixtures not configured')
@pytest.mark.parametrize('task_id',list(CONTRACT))
def test_real_browser_and_adversarial_controls(task_id,tmp_path):
    src=Path(RUNS)/f'task-{int(task_id.split("--")[-1]):02d}';c=CONTRACT[task_id]
    assert E.verify(src,task_id)['pass']
    original=json.loads((src/'trajectory.json').read_text());answer=original['final_answer']
    for text in [answer.upper(), '**Review findings**\n\n'+answer.replace(': ', ' — '), re.sub(r'\$([\d,.]+)(?![\w.])',r'\1 USD',answer), answer.replace(' GB',' gigabytes').replace(' mins',' minutes').replace(' Oz',' ounces')]:E.check_claims(text,c['claims'])
    # Delete each required claim independently. All removed claims must fail.
    for label,pattern in c['claims']:
        changed=re.sub(pattern,'[incorrect]',E.norm(answer),flags=re.I)
        with pytest.raises(ValueError):E.check_claims(changed,c['claims'])
    initial=E.database(src/'initial.db');after=E.database(src/'after.db')
    for table,rule in c.get('state',{}).items():
        for key,row in after[table].items():
            if key in initial[table] and row==initial[table][key]:continue
            for column in ['user_id','sku','quantity','qty','symbol','direction','threshold','course_code','event_eid','game_id','bundle_id','email','note','clientkey','total','payment_method']:
                if column not in row:continue
                changed=copy.deepcopy(after);changed[table][key][column]='WRONG'
                with pytest.raises(ValueError):E.check_state(initial,changed,c)
    dst=tmp_path/'run';shutil.copytree(src,dst,ignore=shutil.ignore_patterns('trajectory.gif'))
    cases=[{'final_answer':''},{'steps':[]},{'task_id':'wrong--0'},{'terminated':False},{'final_answer':'These claims are false. '+answer}]
    for patch in cases:
        t=original|patch;(dst/'trajectory.json').write_text(json.dumps(t))
        with pytest.raises(ValueError):E.verify(dst,task_id)
    foreign=copy.deepcopy(original);foreign['steps'][-1]['url_after']='https://example.com/unrelated'
    (dst/'trajectory.json').write_text(json.dumps(foreign))
    with pytest.raises(ValueError,match='origin'):E.verify(dst,task_id)
    (dst/'trajectory.json').write_text(json.dumps(original))
    image_name=original['steps'][-1]['screenshot_after'];path=dst/'screenshots'/image_name
    from PIL import Image
    Image.new('RGB',(1440,1000),'white').save(path)
    with pytest.raises(ValueError,match='Blank'):E.verify(dst,task_id)
    shutil.copy2(src/'screenshots'/image_name,path)
    for name in ['initial.db','after.db']:
        with sqlite3.connect(dst/name) as db:
            table=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchone()[0]
            db.execute(f'DELETE FROM "{table}" WHERE rowid=(SELECT MIN(rowid) FROM "{table}")')
    with pytest.raises(ValueError,match='Initial state'):E.verify(dst,task_id)


def test_scoped_numeric_claims_accept_natural_values_and_reject_decoys():
    claims=[['Apple price',r'apple[^;]{0,60}?price[^;]{0,30}?333\.02(?!\d|\.\d)']]
    for answer in ['Apple: the price is $333.02.', 'For Apple, price: 333.02 USD.', '**Apple** | price | 333.02 dollars']:
        E.check_claims(answer, claims)
    for answer in ['Apple price is $334.02; reference number 333.02.', 'Apple price is not $333.02.', 'Apple price $334.02; Nvidia price $333.02.']:
        with pytest.raises(ValueError):E.check_claims(answer, claims)
