"""Targeted state/answer controls against known-correct synthetic fixtures."""
import json
import sqlite3
import pytest
from _support import honest_run, run_verifier


@pytest.mark.parametrize('task,sql', [
    (0, "UPDATE bookings SET total=1 WHERE id=1"),
    (0, "UPDATE bookings SET status='cancelled' WHERE id=(SELECT max(id) FROM bookings)"),
    (0, "DELETE FROM booking_passengers WHERE id=1"),
    (0, "UPDATE bookings SET contact_phone='wrong' WHERE id=(SELECT max(id) FROM bookings)"),
    (5, "UPDATE bookings SET fast_track_in=0 WHERE id=(SELECT max(id) FROM bookings)"),
    (8, "UPDATE users SET phone='unrequested' WHERE email='bob.c@test.com'"),
    (8, "UPDATE payment_methods SET expiry='01/20' WHERE last4='4444'"),
    (10, "UPDATE bookings SET total=1 WHERE booking_ref='R2M6YB'"),
    (15, "UPDATE booking_passengers SET cabin_out='small-bag' WHERE booking_id=(SELECT max(id) FROM bookings)"),
])
def test_collateral_and_incomplete_state_rejected(tmp_path, task, sql):
    run = honest_run(tmp_path, task)
    run_verifier(task, run, expect_pass=True)
    with sqlite3.connect(run / 'after.db') as con:con.execute(sql)
    run_verifier(task, run, expect_pass=False)


def test_price_as_reference_is_not_payment(tmp_path):
    run = honest_run(tmp_path, 0);p = run / 'trajectory.json';t = json.loads(p.read_text())
    t['final_answer'] = t['final_answer'].replace('£74.40', '£1.00 (reference ID 74.40)')
    p.write_text(json.dumps(t));run_verifier(0, run, expect_pass=False)


def test_pounds_paraphrase_accepted(tmp_path):
    run = honest_run(tmp_path, 0);p = run / 'trajectory.json';t = json.loads(p.read_text())
    t['final_answer'] = t['final_answer'].replace('£74.40', '74.40 pounds')
    p.write_text(json.dumps(t));run_verifier(0, run, expect_pass=True)
