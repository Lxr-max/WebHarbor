#!/usr/bin/env python3
"""Adversarial verifier tests for the reviewer yahoo_finance contract.

Every test builds a mutated copy of a real honest round-1 package (or a
synthetic forgery) and asserts the verifier's deterministic polarity:
honest evidence passes, every tampering class fails. Honest replays of both
walk rounds are evidence-gated behind WH_YF_EVIDENCE (the review evidence
tree) so the suite is self-contained offline.

Run:  pytest tests/test_verifiers.py -q
      WH_YF_EVIDENCE=<evidence tree> pytest tests/test_verifiers.py -q
"""
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent.parent
VERIFY = SITE / 'verify'
# audit caliber: honest replays come from the audit-track evidence tree
# (wh-yf-audit-evidence/runs, two independent rounds of the f12eff2c
# contract-state container); the r2 review tree (runs_r2) stays as fallback
# history. WH_YF_EVIDENCE overrides both.
EVIDENCE = SITE.parents[5] / 'wh-yf-audit-evidence'
if not EVIDENCE.exists():
    EVIDENCE = Path('/data/zhaoyang-user-projects/websyn/wh-yf-audit-evidence')
if not (EVIDENCE / 'runs').exists():
    EVIDENCE = SITE.parents[5] / 'wh-yf-review-evidence'
if not EVIDENCE.exists():
    EVIDENCE = Path('/data/zhaoyang-user-projects/websyn/wh-yf-review-evidence')
RUNS = EVIDENCE / 'runs'
ROUND1 = RUNS / 'round1'


def _spec(idx):
    ns = {'__file__': str(VERIFY / f'verify_{idx}.py')}
    exec((VERIFY / f'verify_{idx}.py').read_text(), ns)
    return ns['SPEC']


def run_verifier(idx, run_dir):
    proc = subprocess.run(
        [sys.executable, str(VERIFY / f'verify_{idx}.py'),
         '--run_dir', str(run_dir)],
        capture_output=True, text=True, timeout=180)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {'pass': False, 'reason': proc.stdout + proc.stderr}


def clone(idx, dest, round_dir=ROUND1):
    src = Path(round_dir) / f'task_{idx:02d}'
    dst = Path(dest)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def edit_traj(run, **mut):
    p = Path(run) / 'trajectory.json'
    t = json.loads(p.read_text())
    t.update(mut)
    p.write_text(json.dumps(t))


def edit_answer(run, transform):
    p = Path(run) / 'trajectory.json'
    t = json.loads(p.read_text())
    t['final_answer'] = transform(t['final_answer'])
    p.write_text(json.dumps(t))


def edit_db(run, name, sql, params=()):
    p = Path(run) / name
    con = sqlite3.connect(p)
    con.execute(sql, params)
    con.commit()
    con.close()


def _norm(text):
    sys.path.insert(0, str(VERIFY))
    import verify_lib
    return verify_lib.norm(text)


def instantiate(pattern):
    """Build a concrete string that matches a simple forbidden pattern."""
    s = pattern
    s = s.replace(r'\b', '')
    # take the first alternative inside each (?:a|b) / (a|b) group, no parens
    def first_alt(m):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        return inner.split('|')[0]
    s = re.sub(r'\(\?\:([^()]*)\)', first_alt, s)
    s = re.sub(r'\(([^()]*\|[^()]*)\)', first_alt, s)
    s = s.replace(r'\s*', ' ').replace(r'\s+', ' ')
    s = s.replace(r'[^.]{0,40}', ' ').replace(r'[^.]{0,60}', ' ')
    s = s.replace(r'[^.]{0,30}', ' ').replace(r'[^.]{0,80}', ' ')
    s = s.replace(r'[^.]{0,120}', ' ').replace(r'[^.]{0,150}', ' ')
    s = s.replace('/?', '').replace('?]', ']').replace('?', '')
    s = s.replace('\\', '')
    s = re.sub(r'\s+', ' ', s).strip(' .')
    return s


@pytest.fixture(scope='module')
def tmp_work(tmp_path_factory):
    return tmp_path_factory.mktemp('yf_verifier_tests')


# ------------------------------------------------------------- honest runs --

HONEST_IDS = list(range(20))


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_honest_round1_passes(idx, tmp_path):
    result = run_verifier(idx, ROUND1 / f'task_{idx:02d}')
    assert result['pass'], result


@pytest.mark.skipif(not (RUNS / 'round2').exists(),
                    reason='round2 evidence not present')
@pytest.mark.parametrize('idx', HONEST_IDS)
def test_honest_round2_passes(idx, tmp_path):
    result = run_verifier(idx, RUNS / 'round2' / f'task_{idx:02d}')
    assert result['pass'], result


# --------------------------------------------------- package-structure gates --

@pytest.mark.parametrize('idx', HONEST_IDS)
def test_noop_fails(idx, tmp_work):
    """A package that did nothing: no steps, no answer, no state change."""
    run = clone(idx, tmp_work / f'noop_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    traj['steps'] = []
    traj['final_answer'] = ''
    (run / 'trajectory.json').write_text(json.dumps(traj))
    # restore pristine after.db so there is no state delta either
    shutil.copy(run / 'initial.db', run / 'after.db')
    result = run_verifier(idx, run)
    assert not result['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_wrong_task_id_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'wrongid_{idx}')
    edit_traj(run, task_id='YahooFinance--99')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_stale_question_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'stale_{idx}')
    edit_traj(run, task='Old wording that no longer matches tasks.jsonl')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_unfinished_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'unfin_{idx}')
    edit_traj(run, terminated=False)
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [0, 5, 10, 15, 19])
def test_off_origin_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'origin_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    traj['start_url'] = 'http://evil.example.com/'
    (run / 'trajectory.json').write_text(json.dumps(traj))
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [0, 7, 14])
def test_foreign_step_url_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'foreign_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    traj['steps'][2]['url_after'] = 'http://127.0.0.1:9999/quote/AAPL'
    (run / 'trajectory.json').write_text(json.dumps(traj))
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [0, 9, 19])
def test_blank_screenshot_fails(idx, tmp_work):
    from PIL import Image
    run = clone(idx, tmp_work / f'blank_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    name = traj['steps'][1]['screenshot_after']
    img = Image.new('RGB', (1440, 900), (255, 255, 255))
    img.save(run / 'screenshots' / name)
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [0, 4, 12])
def test_missing_screenshot_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'noshot_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    name = traj['steps'][1]['screenshot_after']
    (run / 'screenshots' / name).unlink()
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_navigation_drop_fails(idx, tmp_work):
    """Remove one required page visit -> path gate fails."""
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'navdrop_{idx}')
    traj = json.loads((run / 'trajectory.json').read_text())
    # drop the step whose url_after matches the LAST required path
    import re
    pattern = spec['paths'][-1]
    kept = []
    dropped = False
    for s in traj['steps']:
        u = s.get('url_after', s.get('url', ''))
        if not dropped and re.search(pattern, u, re.I):
            dropped = True
            continue
        kept.append(s)
    assert dropped, f'no step matched {pattern}'
    traj['steps'] = kept
    (run / 'trajectory.json').write_text(json.dumps(traj))
    assert not run_verifier(idx, run)['pass']


# ------------------------------------------------------------- seed gates --

@pytest.mark.parametrize('idx', [0, 8, 16])
def test_tampered_seed_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'seed_{idx}')
    edit_db(run, 'initial.db',
            "UPDATE quotes SET price = 1.0 WHERE symbol = 'AAPL'")
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [0, 3])
def test_wrong_seed_table_count_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'seedcount_{idx}')
    edit_db(run, 'initial.db', 'DELETE FROM news_articles WHERE id = 1')
    assert not run_verifier(idx, run)['pass']


# ------------------------------------------------------- answer-claim gates --

@pytest.mark.parametrize('idx', HONEST_IDS)
def test_forged_answer_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'forge_{idx}')
    edit_answer(run, lambda a: 'I completed everything successfully.')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_claim_corruption_fails(idx, tmp_work):
    """Corrupt ONE claim value in the answer -> that claim gate fails."""
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'corrupt_{idx}')

    def corrupt(answer):
        n = _norm(answer)
        label, pattern = spec['claims'][0]
        corrupted, count = re.subn(pattern, '777777', n, flags=re.I)
        assert count >= 1, label
        return corrupted

    edit_answer(run, corrupt)
    result = run_verifier(idx, run)
    assert not result['pass'], result


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_answer_negation_fails(idx, tmp_work):
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'negate_{idx}')
    label, pattern = spec['claims'][0]
    traj = json.loads((run / 'trajectory.json').read_text())
    n = _norm(traj['final_answer'])
    m = re.search(pattern, n, re.I)
    assert m, label
    # prepend an explicit negation to the matched claim
    traj['final_answer'] = n[:m.start()] + 'not ' + n[m.start():]
    (run / 'trajectory.json').write_text(json.dumps(traj))
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_forbidden_injection_fails(idx, tmp_work):
    spec = _spec(idx)
    if not spec.get('forbidden'):
        pytest.skip('task has no forbidden patterns')
    run = clone(idx, tmp_work / f'forbid_{idx}')
    value = instantiate(spec['forbidden'][0])
    assert re.search(spec['forbidden'][0], _norm(value), re.I), value
    edit_answer(run, lambda a: a + ' Also, just to be safe: ' + value + '.')
    assert not run_verifier(idx, run)['pass']


# ------------------------------------------------------- state-delta gates --

@pytest.mark.parametrize('idx', HONEST_IDS)
def test_no_state_change_fails(idx, tmp_work):
    """Honest answer but the DB was never touched -> state gate fails."""
    run = clone(idx, tmp_work / f'nostate_{idx}')
    shutil.copy(run / 'initial.db', run / 'after.db')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_wrong_state_symbol_fails(idx, tmp_work):
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'wrongsym_{idx}')
    added = spec.get('added', {})
    if 'price_alerts' in added:
        edit_db(run, 'after.db',
                "UPDATE price_alerts SET symbol='ZZZZ' WHERE id=7")
    elif 'watch_items' in added:
        edit_db(run, 'after.db',
                "UPDATE watch_items SET symbol='ZZZZ' WHERE id=15")
    else:
        pytest.skip('no single-row mutation target')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_extra_state_row_fails(idx, tmp_work):
    run = clone(idx, tmp_work / f'extra_{idx}')
    edit_db(run, 'after.db',
            "INSERT INTO price_alerts (user_id, symbol, direction, threshold,"
            " note, created_at) VALUES (2, 'AAPL', 'above', 1.0, 'x',"
            " '2026-09-30')")
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', HONEST_IDS)
def test_missing_state_row_fails(idx, tmp_work):
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'missing_{idx}')
    if 'price_alerts' in spec.get('added', {}):
        edit_db(run, 'after.db', 'DELETE FROM price_alerts WHERE id = 7')
    elif 'watch_items' in spec.get('added', {}):
        edit_db(run, 'after.db', 'DELETE FROM watch_items WHERE id = 15')
    else:
        pytest.skip('no removable expected row')
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [1, 9])
def test_wrong_signup_password_fails(idx, tmp_work):
    """The new account's bcrypt hash must verify TestPass123!."""
    run = clone(idx, tmp_work / f'badpw_{idx}')
    edit_db(run, 'after.db',
            "UPDATE users SET password_hash="
            "'$2b$12$KIXQeJrbrNm0HFyzAhS8XOxTyBBrTtGgVwN3gHh3Xq9W1zZrP1a2e'"
            " WHERE id = 5")
    assert not run_verifier(idx, run)['pass']


@pytest.mark.parametrize('idx', [12, 13, 19])
def test_missing_removal_fails(idx, tmp_work):
    """Tasks that must remove a row: undo the removal -> state gate fails."""
    spec = _spec(idx)
    run = clone(idx, tmp_work / f'unremove_{idx}')
    if 'watch_items' in spec.get('removed', {}):
        edit_db(run, 'after.db',
                "INSERT INTO watch_items (user_id, symbol, added_at) VALUES"
                " (3, 'UNH', '2026-09-30')")
    elif 'price_alerts' in spec.get('removed', {}):
        edit_db(run, 'after.db',
                "INSERT INTO price_alerts (user_id, symbol, direction,"
                " threshold, note, created_at) VALUES"
                " (1, 'TSLA', 'above', 480.0, NULL, '2026-09-30')")
    assert not run_verifier(idx, run)['pass']


# ------------------------------------------------------- cross-task confusion --

@pytest.mark.parametrize('i', HONEST_IDS)
def test_cross_task_confusion_fails(i, tmp_work):
    """Honest package of task i graded by task j's verifier must fail."""
    for j in HONEST_IDS:
        if j == i:
            continue
        result = run_verifier(j, ROUND1 / f'task_{i:02d}')
        assert not result['pass'], (i, j)


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-q']))
