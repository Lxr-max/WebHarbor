"""Contract regressions runnable without a contributor's private filesystem.

Set WEBHARBOR_REVIEW_RUNS to a task-00/... browser evidence root for the
optional end-to-end fixture suite. Those runs are external review artifacts.
"""
import importlib.util
import json
import os
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_contract_engine', HERE / 'contract_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
CONTRACTS = json.loads((HERE / 'contract.json').read_text())
TASKS = {row['id']: row for row in map(json.loads, (HERE.parent / 'tasks.jsonl').read_text().splitlines())}

@pytest.mark.parametrize('task_id', list(CONTRACTS))
def test_contract_matches_published_task(task_id):
    assert CONTRACTS[task_id]['task'] == TASKS[task_id]['ques']
    assert CONTRACTS[task_id]['claims'] and CONTRACTS[task_id]['paths']
    assert len(CONTRACTS[task_id]['initial_digest']) == 64

@pytest.mark.parametrize('task_id', list(CONTRACTS))
def test_empty_or_self_reported_answers_fail(task_id):
    for answer in ['', 'Done. I successfully completed every requested step.']:
        with pytest.raises(ValueError):
            engine.check_claims(answer, CONTRACTS[task_id]['claims'])


def test_unrelated_state_is_preserved():
    initial = {'saved': {'[1]': {'id':1, 'owner':1, 'item':'existing'}}}
    spec = {'initial_digest':engine.digest(initial), 'state':{'saved':{'added':[{'id':2,'owner':1,'item':'target'}]}}}
    correct = {'saved': initial['saved'] | {'[2]': {'id':2, 'owner':1,'item':'target'}}}
    engine.check_state(initial, correct, spec)
    for altered in [
        {'saved':{'[2]':{'id':2,'owner':1,'item':'target'}}},
        {'saved':initial['saved'] | {'[2]':{'id':2,'owner':2,'item':'target'}}},
        {'saved':initial['saved'] | {'[2]':{'id':2,'owner':1,'item':'wrong'}}},
        initial,
    ]:
        with pytest.raises(ValueError):engine.check_state(initial, altered, spec)

@pytest.mark.skipif(not os.environ.get('WEBHARBOR_REVIEW_RUNS'), reason='External real-browser evidence not configured')
@pytest.mark.parametrize('task_id', list(CONTRACTS))
def test_recorded_browser_run(task_id):
    number = int(task_id.rsplit('--',1)[1])
    run = Path(os.environ['WEBHARBOR_REVIEW_RUNS']) / f'task-{number:02}'
    assert engine.verify(run, task_id)['pass']
