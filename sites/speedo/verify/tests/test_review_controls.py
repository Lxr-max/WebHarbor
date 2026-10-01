"""Reviewer controls: copies of synthetic fixtures, not browser trajectories."""
import json
import sqlite3
from pathlib import Path
import pytest
from _support import *

def change_answer(run, fn):
    p=run/'trajectory.json';t=json.loads(p.read_text());t['final_answer']=fn(t['final_answer']);p.write_text(json.dumps(t))


def judge_fixture(tmp_path,n,sql=None,answer=None,expect=True):
    run=honest_run(tmp_path,n);after=mutate_after_db(tmp_path,n)
    if sql:
        with sqlite3.connect(after) as c:
            for query in sql:c.execute(query)
    if answer:change_answer(run,answer)
    code,result=run_verifier(n,run,after)
    assert result['pass'] is expect,result
    return run,after


def test_delivery_recipient_rejected(tmp_path):
    judge_fixture(tmp_path,0,["UPDATE orders SET ship_name='Wrong Person' WHERE id=8"],expect=False)


def test_order_item_wrong_parent_rejected(tmp_path):
    judge_fixture(tmp_path,0,["UPDATE order_items SET order_id=1 WHERE id=12"],expect=False)


def test_prior_order_preserved(tmp_path):
    judge_fixture(tmp_path,0,["UPDATE orders SET status='Cancelled' WHERE id=1"],expect=False)


def test_unspecified_email_is_not_a_hidden_requirement(tmp_path):
    judge_fixture(tmp_path,0,["UPDATE orders SET email='another@example.com' WHERE id=8"])


def test_express_under_ten_is_valid(tmp_path):
    judge_fixture(tmp_path,20,["UPDATE orders SET shipping_method='Express Delivery',shipping=8.99,total=15.74 WHERE id=8"],lambda a:a.replace('12.74','15.74'))


def test_new_wishlist_owned_by_new_user(tmp_path):
    judge_fixture(tmp_path,14,["UPDATE wishlist_items SET user_id=1 WHERE id=19"],expect=False)


def test_wrong_new_password_rejected(tmp_path):
    judge_fixture(tmp_path,14,["UPDATE users SET password_hash='not-a-password-hash' WHERE id=5"],expect=False)


def test_other_users_wishlist_preserved(tmp_path):
    judge_fixture(tmp_path,1,["UPDATE wishlist_items SET product_id=100 WHERE user_id=1 AND id=1"],expect=False)
