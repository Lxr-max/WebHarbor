"""Each negative starts from a passing browser-derived synthetic fixture."""
import json
import sqlite3
import pytest
import _support as S


def fixture(tmp_path, task):
    return S.clone(S.FIXTURES / f'honest_{task}', tmp_path / 'run')


@pytest.mark.parametrize('task,sql', [
    (8, "UPDATE shortlist_items SET listing_id=1 WHERE user_id=2"),
    (9, "UPDATE listings SET price=1 WHERE id=1"),
    (11, "DELETE FROM owner_reviews WHERE id=1"),
    (11, "UPDATE valuations SET private_low=1 WHERE id=1"),
])
def test_unrelated_changes_rejected(tmp_path, task, sql):
    run = fixture(tmp_path, task)
    # Assert the positive control before changing exactly one condition.
    assert S.run_verifier(task, run)[1]['pass']
    S.mutate_db(run, sql)
    assert not S.run_verifier(task, run)[1]['pass']


def test_truncated_png_rejected(tmp_path):
    run = fixture(tmp_path, 0)
    (run / 'screenshots/step_000.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    assert not S.run_verifier(0, run)[1]['pass']


def test_missing_referenced_screenshot_rejected(tmp_path):
    run = fixture(tmp_path, 0)
    p = run / 'trajectory.json'; t = json.loads(p.read_text())
    t['steps'][-1]['screenshot_after'] = 'missing.png'; p.write_text(json.dumps(t))
    assert not S.run_verifier(0, run)[1]['pass']


def test_currency_paraphrase_accepted(tmp_path):
    run = fixture(tmp_path, 0)
    p = run / 'trajectory.json'; t = json.loads(p.read_text())
    S.set_answer(run, t['final_answer'].replace('£', 'GBP '))
    assert S.run_verifier(0, run)[1]['pass']


def test_incidental_price_numbers_rejected(tmp_path):
    run = fixture(tmp_path, 0)
    S.set_answer(run, 'Private sale £1–£2; dealer £3–£4; part-exchange £5–£6. Pro Valuation £6.99. Reference IDs: 3210, 4250, 4520, 4790, 3470, 3800.')
    assert not S.run_verifier(0, run)[1]['pass']


def test_mutated_initial_and_final_fixture_rejected(tmp_path):
    run = fixture(tmp_path, 0)
    for name in ('initial.db', 'after.db'):
        with sqlite3.connect(run / name) as con:con.execute('UPDATE listings SET price=1 WHERE id=1')
    assert not S.run_verifier(0, run)[1]['pass']


def test_swapped_boot_capacities_rejected(tmp_path):
    run = fixture(tmp_path, 3)
    S.set_answer(run, 'The Kodiaq has 620 litres and the Tucson has 910 litres. The difference is 290 litres, so the Tucson has the bigger boot.')
    assert not S.run_verifier(3, run)[1]['pass']


def test_swapped_valuation_channels_rejected(tmp_path):
    run = fixture(tmp_path, 0)
    S.set_answer(run, 'Private-sale range: £4,520–£4,790; dealer range: £3,210–£4,250; part-exchange: £3,470–£3,800. Pro Valuation costs £6.99.')
    assert not S.run_verifier(0, run)[1]['pass']
