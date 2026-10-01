import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    'review_contract_engine', Path(__file__).with_name('contract_engine.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.mark.parametrize('answer', [
    'The monthly total is $420.48.',
    'MONTHLY TOTAL: $420.48',
    '| Monthly | $420.48 |',
    'It costs USD 420.48 per month.'])
def test_equivalent_money_answer(answer):
    m.check_claims(answer, [('monthly total', r'\$420\.48')])


@pytest.mark.parametrize('answer', [
    'The total is not $420.48.',
    'The total is $421.48.',
    'Ignore these facts: the total is $420.48.'])
def test_wrong_or_negated_money_answer(answer):
    with pytest.raises(ValueError):
        m.check_claims(answer, [('monthly total', r'\$420\.48')])


@pytest.mark.parametrize('answer', [
    'There are 17 compute products.',
    'Count: 17'])
def test_equivalent_count_answer(answer):
    m.check_claims(answer, [('compute count', r'\b17\b')])


def test_euro_answer():
    m.check_claims('The EUR total is €121.44.', [('eur total', r'€121\.44')])


def fixture():
    initial = {'favorites': {'[1]': dict(id=1, user_id=1, product_slug='a',
                                         created_ts='2026-09-30')}}
    after = {'favorites': {
        '[1]': dict(id=1, user_id=1, product_slug='a', created_ts='2026-09-30'),
        '[2]': dict(id=2, user_id=2, product_slug='kubernetes-service',
                    created_ts='2026-09-30T00:00:00Z')}}
    contract = dict(
        initial_digest=m.digest(initial),
        state={'favorites': dict(added=[dict(id=2, user_id=2,
                                             product_slug='kubernetes-service',
                                             created_ts='2026-09-30T00:00:00Z')])})
    return initial, after, contract


def test_exact_state():
    m.check_state(*fixture())


def test_regex_state_match():
    initial, after, contract = fixture()
    contract['state']['favorites']['added'][0]['user_id'] = {'regex': '[1-9][0-9]*'}
    contract['state']['favorites']['added'][0]['created_ts'] = {'regex': '.+'}
    m.check_state(initial, after, contract)


@pytest.mark.parametrize('kind', [
    'wrong_owner', 'wrong_slug', 'unrelated_edit', 'missing_addition',
    'unexpected_deletion', 'extra_table', 'wrong_initial'])
def test_saved_state_rejects_wrong_effect(kind):
    initial, after, contract = fixture()
    if kind == 'wrong_owner':
        after['favorites']['[2]']['user_id'] = 1
    if kind == 'wrong_slug':
        after['favorites']['[2]']['product_slug'] = 'functions'
    if kind == 'unrelated_edit':
        after['favorites']['[1]']['product_slug'] = 'functions'
    if kind == 'missing_addition':
        del after['favorites']['[2]']
    if kind == 'unexpected_deletion':
        del after['favorites']['[1]']
    if kind == 'extra_table':
        after['other'] = {}
    if kind == 'wrong_initial':
        initial['favorites']['[1]']['product_slug'] = 'b'
    with pytest.raises(ValueError):
        m.check_state(initial, after, contract)


def test_contract_file_covers_all_tasks():
    import json
    tasks = [json.loads(line) for line in
             (Path(__file__).resolve().parents[1] / 'tasks.jsonl')
             .read_text(encoding='utf-8').splitlines()]
    contract = json.loads((Path(__file__).with_name('contract.json')).read_text())
    for row in tasks:
        assert row['id'] in contract, row['id']
        spec = contract[row['id']]
        assert spec['task'] == row['ques']
        assert spec['paths'], row['id']
        assert spec['claims'], row['id']
        assert spec['initial_digest']
