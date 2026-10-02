import copy
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('review_contract_engine',Path(__file__).with_name('contract_engine.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.mark.parametrize('answer',['Phone costs $17.65.','PHONE COSTS $17.65.','| Phone | costs $17.65 |'])
def test_equivalent_entity_price(answer):
    m.check_claims(answer,[('price',r'phone.{0,35}\$17\.65')])

@pytest.mark.parametrize('answer',['Phone does not cost $17.65.',"Phone doesn't cost $17.65.",'Phone costs $19; reference number $17.65.','Phone costs $19.','The following is false: Phone costs $17.65.'])
def test_wrong_or_negated_entity_price(answer):
    with pytest.raises(ValueError):m.check_claims(answer,[('price',r'phone.{0,35}\$17\.65')])

def fixture():
    initial={'items':{'[1]':dict(id=1,user_id=1,qty=1)}}
    after={'items':{'[1]':dict(id=1,user_id=1,qty=1),'[2]':dict(id=2,user_id=2,qty=3)}}
    contract=dict(initial_digest=m.digest(initial),state={'items':dict(added=[dict(id={'regex':'[1-9][0-9]*'},user_id=2,qty=3)])})
    return initial,after,contract

def test_exact_state():
    m.check_state(*fixture())

@pytest.mark.parametrize('kind',['wrong_owner','wrong_quantity','unrelated_edit','missing_addition','unexpected_deletion','extra_table','wrong_initial'])
def test_saved_state_rejects_wrong_effect(kind):
    initial,after,contract=fixture()
    if kind=='wrong_owner':after['items']['[2]']['user_id']=1
    if kind=='wrong_quantity':after['items']['[2]']['qty']=2
    if kind=='unrelated_edit':after['items']['[1]']['qty']=2
    if kind=='missing_addition':del after['items']['[2]']
    if kind=='unexpected_deletion':del after['items']['[1]']
    if kind=='extra_table':after['other']={}
    if kind=='wrong_initial':initial['items']['[1]']['qty']=0
    with pytest.raises(ValueError):m.check_state(initial,after,contract)

def test_json_cart_ignores_order_but_requires_quantity_and_variant():
    expected={'json_rows':[dict(product=1,qty=2,color={'one_of':['Red','Blue']}),dict(product=2,qty=1,color='Black')]}
    assert m.matches('[{"product":2,"qty":1,"color":"Black"},{"product":1,"qty":2,"color":"Red"}]',expected)
    assert not m.matches('[{"product":2,"qty":2,"color":"Black"},{"product":1,"qty":2,"color":"Red"}]',expected)
    assert not m.matches('[{"product":2,"qty":1,"color":"Black"},{"product":1,"qty":2,"color":"Green"}]',expected)

def test_relation_cannot_link_unrelated_parent():
    initial={'parents':{},'children':{}};after={'parents':{'[3]':{'id':3}},'children':{'[1]':{'parent_id':2}}}
    with pytest.raises(ValueError):m.check_relations(initial,after,dict(left='parents',right='children',foreign_key='parent_id'))
