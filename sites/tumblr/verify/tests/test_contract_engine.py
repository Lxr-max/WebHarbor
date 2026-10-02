"""Regression controls for the site-contained offline grading contract."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

MODULE = Path(__file__).resolve().parents[1] / 'contract_engine.py'
spec = importlib.util.spec_from_file_location('review_contract', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_natural_numeric_and_case_equivalents():
    m.check_claims('The model costs $1,234. Two units remain.', [('price', r'model costs \$1234'), ('quantity', r'2 units')])


@pytest.mark.parametrize('answer', ['The following is false: model costs $1234', 'The model does not cost $1234', 'The model costs $1235; reference 1234'])
def test_false_or_unrelated_price_fails(answer):
    with pytest.raises(ValueError):
        m.check_claims(answer, [('price', r'model (?:costs|cost) \$1234')])


def test_exact_delta_preserves_other_accounts_and_quantity():
    initial={'cart':{'[1]':{'id':1,'user':1,'product':10,'qty':1},'[2]':{'id':2,'user':2,'product':20,'qty':3}}}
    contract={'initial_digest':m.digest(initial),'state':{'cart':{'updated':{'[1]':{'qty':2}}}}}
    after=copy.deepcopy(initial);after['cart']['[1]']['qty']=2
    m.check_state(initial,after,contract)
    for user,key,value in [(1,'qty',1),(2,'qty',2),(1,'product',11)]:
        bad=copy.deepcopy(after);bad['cart'][f'[{user}]'][key]=value
        with pytest.raises(ValueError):m.check_state(initial,bad,contract)


def test_initial_seed_tampering_fails_even_if_after_matches():
    original={'users':{'[1]':{'id':1,'name':'Alice'}}}
    altered={'users':{'[1]':{'id':1,'name':'Bob'}}}
    with pytest.raises(ValueError):m.check_state(altered,altered,{'initial_digest':m.digest(original)})


def test_tag_order_is_not_an_artificial_requirement():
    assert m.matches('["wishlist", "cottagecore"]', {'json_set':['cottagecore','wishlist']})
    assert not m.matches('["cottagecore", "unrelated"]', {'json_set':['cottagecore','wishlist']})


def test_false_statement_crime_is_not_answer_negation():
    m.check_claims('The indictment alleges a false statement in a naturalization proceeding.', [('charge',r'false statement')])
