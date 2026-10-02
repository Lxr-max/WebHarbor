"""Adversarial controls for identity and unrelated state preservation."""
import json
import sqlite3
import pytest
from test_verifiers import honest_run
from _support import run_verifier


@pytest.mark.parametrize('sql', [
    'UPDATE food_orders SET user_id=2 WHERE id=6',
    'UPDATE food_orders SET location_id=405 WHERE id=6',
    "UPDATE users SET phone='tampered' WHERE id=4",
])
def test_wrong_owner_location_or_unrelated_edit_fails(tmp_path, sql):
    run, after = honest_run(tmp_path, 0)
    with sqlite3.connect(after) as db:
        db.execute(sql)
    assert not run_verifier(0, run)['pass']


@pytest.mark.parametrize('key,value', [('task_id', "Raising Cane's--1"), ('terminated', False), ('final_url', 'https://example.com/')])
def test_evidence_identity_fails(tmp_path, key, value):
    run, _ = honest_run(tmp_path, 0)
    path = run / 'trajectory.json'
    traj = json.loads(path.read_text()); traj[key] = value
    path.write_text(json.dumps(traj))
    assert not run_verifier(0, run)['pass']


def test_changed_initial_state_fails(tmp_path):
    run, _ = honest_run(tmp_path, 19)
    with sqlite3.connect(run / 'initial.db') as db:
        db.execute("UPDATE users SET phone='tampered' WHERE id=4")
    assert not run_verifier(19, run)['pass']
