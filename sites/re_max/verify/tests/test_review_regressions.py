"""Existing rows must survive otherwise permitted stateful changes."""
import sqlite3
import _support as S


def test_existing_favorite_owner_cannot_change(tmp_path):
    run = S.clone(S.honest_dir(10), tmp_path / 'tampered')
    with sqlite3.connect(run / 'after.db') as db:
        db.execute('UPDATE favorites SET user_id=4 WHERE id=(SELECT min(id) FROM favorites)')
    code, verdict = S.run_verifier(10, run)
    assert code != 0 and not verdict['pass']


def test_read_only_initial_rows_are_frozen(tmp_path):
    run = S.clone(S.honest_dir(0), tmp_path / 'tampered')
    with sqlite3.connect(run / 'initial.db') as db:
        db.execute("UPDATE users SET first_name='tampered' WHERE id=1")
    code, verdict = S.run_verifier(0, run)
    assert code != 0 and not verdict['pass']


def test_natural_rate_summary_equivalents(tmp_path):
    run = S.clone(S.honest_dir(15), tmp_path / 'natural')
    S.set_answer(run, 'The Fed raised rates to 3.75–4%, with a 12 to 0 vote at the September 15 and 16, 2026 meeting. HomeHQ confirmed the subscription.')
    code, verdict = S.run_verifier(15, run)
    assert code == 0 and verdict['pass'], verdict


def test_natural_concession_range(tmp_path):
    run = S.clone(S.honest_dir(14), tmp_path / 'natural')
    S.set_answer(run, S.HONEST_ANSWERS[14].replace('2% to 9%', '2–9%'))
    code, verdict = S.run_verifier(14, run)
    assert code == 0 and verdict['pass'], verdict
