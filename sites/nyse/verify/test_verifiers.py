"""Portable contract controls. Set WEBHARBOR_REVIEW_RUNS to task-00/... runs.

The optional browser-fixture tests operate on copies and never change original
evidence. Synthetic state/claim controls declare expected failures explicitly.
"""
from pathlib import Path
import copy
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import pytest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review_engine_'+HERE.parent.name,HERE/'contract_engine.py')
E=importlib.util.module_from_spec(spec);spec.loader.exec_module(E)
CONTRACT=json.loads((HERE/'contract.json').read_text())
RUNS=os.environ.get('WEBHARBOR_REVIEW_RUNS')

def test_task_contract_matches_prompts():
    tasks=[json.loads(l) for l in (HERE.parent/'tasks.jsonl').read_text().splitlines()]
    assert {t['id'] for t in tasks}==set(CONTRACT)
    for task in tasks:
        c=CONTRACT[task['id']]
        assert c['task']==task['ques']
        assert c['claims'] and c['paths']
        assert isinstance(task['judge_rubric'],str)
        for claim in c['claims']:re.compile(claim['pattern'])

@pytest.mark.parametrize('task_id',list(CONTRACT))
def test_blank_and_wrong_answers_fail(task_id):
    for answer in ['', 'Everything costs $999999.99; nothing was saved.', 'These claims are false.']:
        with pytest.raises(ValueError):E.check_claims(answer,CONTRACT[task_id])

@pytest.mark.parametrize('change',['remove','update','add'])
def test_exact_state_protects_unrelated_rows(change):
    before={'saved':{'[1]':{'id':1,'owner':7,'item':'existing'}}}
    after=copy.deepcopy(before);contract={'initial_digest':E.digest(before),'state':{}}
    if change=='remove':after['saved'].clear()
    elif change=='update':after['saved']['[1]']['owner']=8
    else:after['saved']['[2]']={'id':2,'owner':7,'item':'unrequested'}
    with pytest.raises(ValueError):E.check_state(before,after,contract)

@pytest.mark.skipif(not RUNS,reason='Set WEBHARBOR_REVIEW_RUNS to saved browser fixtures')
@pytest.mark.parametrize('task_id',list(CONTRACT))
def test_browser_positive_and_negative_controls(task_id,tmp_path):
    idx=int(task_id.split('--')[-1]);src=Path(RUNS)/f'task-{idx:02d}'
    assert E.verify(src,task_id)['pass']
    dst=tmp_path/'run';shutil.copytree(src,dst)
    original=json.loads((dst/'trajectory.json').read_text())
    # Equivalent case and whitespace must not change the factual verdict.
    E.check_claims('  '+original['final_answer'].upper().replace('\n','  ')+'  ', CONTRACT[task_id])
    initial=E.database(src/'initial.db');after=E.database(src/'after.db')
    for table,rule in CONTRACT[task_id].get('state',{}).items():
        for key,row in after[table].items():
            if key in initial[table]:continue
            for column in ['user_id','product_slug','model_code','qty','symbol','direction','threshold','section_id','event_id','program_id','email','message']:
                if column not in row:continue
                changed=copy.deepcopy(after);changed[table][key][column]='WRONG'
                with pytest.raises(ValueError):E.check_state(initial,changed,CONTRACT[task_id])
    mutations={
        'empty answer':lambda t:t.update(final_answer=''),
        'wrong task':lambda t:t.update(task_id='wrong--0'),
        'unfinished':lambda t:t.update(terminated=False),
        'answer only':lambda t:t.update(steps=[]),
        'false disclaimer':lambda t:t.update(final_answer='These claims are false. '+t['final_answer']),
        'wrong required fact':lambda t:t.update(final_answer=re.sub(CONTRACT[task_id]['claims'][0]['pattern'], '[incorrect]', E.norm(t['final_answer']), flags=re.I)),
    }
    for label,mutate in mutations.items():
        t=copy.deepcopy(original);mutate(t);(dst/'trajectory.json').write_text(json.dumps(t))
        with pytest.raises(ValueError):E.verify(dst,task_id)
    (dst/'trajectory.json').write_text(json.dumps(original))
    # Consistently corrupt both snapshots: must fail initial-fixture identity.
    for name in ['initial.db','after.db']:
        with sqlite3.connect(dst/name) as con:
            tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            table=next(t for t in tables if con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
            con.execute(f'DELETE FROM "{table}" WHERE rowid=(SELECT MIN(rowid) FROM "{table}")')
    with pytest.raises(ValueError,match='Initial state'):E.verify(dst,task_id)


@pytest.mark.parametrize('control',json.loads((HERE/'answer_controls.json').read_text()))
def test_targeted_answer_equivalents_and_counterexamples(control):
    if control['expected']:
        E.check_claims(control['answer'],CONTRACT[control['task']])
    else:
        with pytest.raises(ValueError):
            E.check_claims(control['answer'],CONTRACT[control['task']])
