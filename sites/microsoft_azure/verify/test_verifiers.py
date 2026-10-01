"""Adversarial verifier tests for the microsoft_azure review contract.

Proves, per task, that the contract engine is fail-closed against every
shortcut class while still passing honest evidence:

  * no-op trajectories (homepage only, untouched seed) FAIL for all 20 tasks
  * answer-only shortcuts (correct claims, no browser evidence) FAIL
  * wrong / negated / rejected claims FAIL
  * wrong-owner, wrong-slug, unrelated-edit, unexpected-deletion,
    extra-table and stale-initial state deltas FAIL
  * corrupt / blank screenshots FAIL; foreign origins FAIL
  * unfinished attempts and task-wording confusion FAIL
  * the honest form-submission URL shapes (category=&q=...) satisfy the
    path patterns (regression test for the path calibration fix)
  * a full honest-shape control fixture PASSES end to end (non-vacuous)

The control fixture drives the real Flask app (CSRF on) on a fresh seeded
database, so the state delta and the graded answer both come from the app
itself; only the screenshots are generated PNGs (the engine checks PNG
validity and non-blankness, not pixels — disclosed engine limitation).
"""
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
sys.path.insert(0, str(SITE))
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location('ce', HERE / 'contract_engine.py')
ce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ce)

CONTRACT = json.loads((HERE / 'contract.json').read_text())
TASK_IDS = [f'Microsoft Azure--{i}' for i in range(20)]


def seed_db(tmp: Path) -> Path:
    """Materialize a fresh deterministic seed database via the real app."""
    os.environ['AZURE_DB_URI'] = f'sqlite:///{tmp / "microsoft_azure.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed')):
            del sys.modules[mod]
    import app as A  # noqa: F401  (import seeds the database)
    return tmp / 'microsoft_azure.db'


BANDS = [(200, 30, 30), (30, 200, 30), (30, 30, 220), (220, 220, 30),
         (30, 220, 220), (220, 30, 220), (250, 250, 250), (10, 10, 10),
         (120, 200, 40), (40, 40, 160)]


def make_png(path: Path, hue: int, blank: bool = False) -> None:
    """A valid, non-blank PNG (or an intentionally blank one). Ten solid
    high-contrast bands survive the engine's 32x32 downscale with >= 8
    distinct colors; a uniform white image does not (blank gate)."""
    from PIL import Image
    if blank:
        img = Image.new('RGB', (640, 400), (255, 255, 255))
    else:
        img = Image.new('RGB', (640, 400))
        for i, band in enumerate(BANDS):
            img.paste(((band[0] + hue) % 256, band[1], band[2]), (0, i * 40, 640, (i + 1) * 40))
    img.save(path, 'PNG')


class Run:
    """A synthetic browser-run directory shaped exactly like honest runs."""

    def __init__(self, root: Path, task_id: str, urls, answer, db_seed: Path,
                 db_after: Path = None, screenshots='gradient', terminated=True,
                 task_text=None, origin='http://localhost:40133'):
        self.dir = root
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / 'screenshots').mkdir(exist_ok=True)
        shots = []
        for i, u in enumerate(urls):
            name = f'shot_{i:03d}.png'
            if screenshots == 'gradient':
                make_png(self.dir / 'screenshots' / name, (i * 37) % 255)
            elif screenshots == 'blank':
                make_png(self.dir / 'screenshots' / name, 0, blank=True)
            elif screenshots == 'corrupt':
                (self.dir / 'screenshots' / name).write_bytes(b'\x89PNG\r\n\x1a\nGARBAGE')
            shots.append(name)
        steps = [{'url': u, 'url_after': u, 'screenshot_after': s,
                  'screenshot': s, 'action': 'goto', 'thought': 'step'}
                 for u, s in zip(urls, shots)]
        text = task_text if task_text is not None else CONTRACT[task_id]['task']
        (self.dir / 'trajectory.json').write_text(json.dumps({
            'task_id': task_id, 'task': text, 'start_url': origin + '/',
            'terminated': terminated, 'termination_reason': 'agent_done' if terminated else 'max_steps',
            'steps': steps, 'final_answer': answer}))
        shutil.copy2(db_seed, self.dir / 'initial.db')
        shutil.copy2(db_after if db_after else db_seed, self.dir / 'after.db')


def expect_fail(run_dir: Path, task_id: str, why: str):
    with pytest.raises(ValueError) as exc:
        ce.verify(str(run_dir), task_id)
    assert why in str(exc.value), f'{task_id}: expected {why!r}, got {exc.value}'


@pytest.fixture(scope='module')
def seed(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('seed')
    db = seed_db(tmp)
    yield db
    shutil.rmtree(tmp, ignore_errors=True)


def noop_run(tmp_path, seed, task_id, answer='Done.'):
    """Homepage-only trajectory with the untouched seed as after-state."""
    return Run(tmp_path / f'noop-{task_id}', task_id,
               ['http://localhost:40133/'], answer, seed, seed)


# ---------------------------------------------------------------- no-op FAIL --

@pytest.mark.parametrize('task_id', TASK_IDS)
def test_noop_fails_for_every_task(tmp_path, seed, task_id):
    run = noop_run(tmp_path, seed, task_id)
    expect_fail(run.dir, task_id, 'Required page evidence missing')


def test_noop_with_claim_words_still_fails(tmp_path, seed):
    """An answer that recites correct facts but did nothing must fail."""
    spec = CONTRACT['Microsoft Azure--2']
    answer = ('Three always-on Linux D4s v5 virtual machines in West US 2 cost '
              '$420.48 per month, saved as Production web tier at $420.48.')
    run = Run(tmp_path / 'noop-claims', 'Microsoft Azure--2',
              ['http://localhost:40133/'], answer, seed, seed)
    expect_fail(run.dir, 'Microsoft Azure--2', 'Required page evidence missing')


# ------------------------------------------------------ shortcut FAILs --

def test_answer_without_steps_fails(tmp_path, seed):
    run = noop_run(tmp_path, seed, 'Microsoft Azure--2')
    traj = json.loads((run.dir / 'trajectory.json').read_text())
    traj['final_answer'] = ('The monthly total is $420.48 and the saved estimate '
                            'Production web tier lists $420.48.')
    traj['steps'] = []
    (run.dir / 'trajectory.json').write_text(json.dumps(traj))
    expect_fail(run.dir, 'Microsoft Azure--2', 'Missing browser evidence')


def test_unfinished_attempt_fails(tmp_path, seed):
    run = Run(tmp_path / 'unfinished', 'Microsoft Azure--2',
              ['http://localhost:40133/', 'http://localhost:40133/pricing/calculator/'],
              'Unfinished.', seed, seed, terminated=False)
    expect_fail(run.dir, 'Microsoft Azure--2', 'Unfinished attempt')


def test_foreign_origin_fails(tmp_path, seed):
    run = Run(tmp_path / 'origin', 'Microsoft Azure--2',
              ['http://localhost:40133/', 'http://example.com/pricing/calculator/'],
              'x', seed, seed)
    expect_fail(run.dir, 'Microsoft Azure--2', 'Browser evidence changes origin')


def test_task_wording_confusion_fails(tmp_path, seed):
    run = Run(tmp_path / 'confusion', 'Microsoft Azure--2',
              ['http://localhost:40133/', 'http://localhost:40133/pricing/calculator/'],
              'x', seed, seed, task_text=CONTRACT['Microsoft Azure--5']['task'])
    expect_fail(run.dir, 'Microsoft Azure--2', 'Wrong task identity or wording')


def t0_run_with_correct_state(tmp_path, seed, answer, tid='Microsoft Azure--0'):
    """A run whose paths, screenshots and state delta are all correct, so any
    failure isolates the claim gate."""
    after = db_with_favorite(seed, tmp_path / 'after-ok.db', 2, 'kubernetes-service')
    return Run(tmp_path / f'claims-{answer[:12]!r}', tid, full_urls_for(tid),
               answer, seed, after)


def test_wrong_answer_fails_on_its_claim(tmp_path, seed):
    """All claims correct except the compute count (17 -> 18)."""
    answer = ('18 compute products. The first product is App Service: a fully '
              'managed PaaS solution, 11 section headings. The second product, '
              'Azure Container Apps, does not link to a pricing details page. '
              'Azure Virtual Machines: scalable, on-demand computing. The '
              'Kubernetes search returns 1 result. The account page shows 1 '
              'favorite.')
    run = t0_run_with_correct_state(tmp_path, seed, answer)
    expect_fail(run.dir, 'Microsoft Azure--0', 'Missing or incorrect compute count')


def test_negated_answer_fails(tmp_path, seed):
    answer = ('17 compute products. The first product is App Service: not '
              'managed PaaS solution, 11 section headings. The second product, '
              'Azure Container Apps, does not link to a pricing details page. '
              'Azure Virtual Machines: scalable, on-demand computing. The '
              'Kubernetes search returns 1 result. The account page shows 1 '
              'favorite.')
    run = t0_run_with_correct_state(tmp_path, seed, answer)
    expect_fail(run.dir, 'Microsoft Azure--0', 'Negated first description')


def test_count_claim_collision_is_a_known_limitation(tmp_path, seed):
    """FINDING (documented, to be tightened in the fix round): two count claims
    with the same regex (T0's 'kubernetes results' \\b1\\b and 'favorites
    count' \\b1\\b) cannot be graded independently — an answer that satisfies
    one automatically satisfies the other, so '1 result ... 2 favorites'
    still passes the claim gate. This test pins the current behavior so any
    change is conscious; the fix should scope count claims locally (e.g.
    'favorites?\\W{0,40}\\b1\\b')."""
    answer = ('17 compute products. The first product is App Service: a fully '
              'managed PaaS solution, 11 section headings. The second product, '
              'Azure Container Apps, does not link to a pricing details page. '
              'Azure Virtual Machines: scalable, on-demand computing. The '
              'Kubernetes search returns 1 result. The account page shows 2 '
              'favorites.')
    run = t0_run_with_correct_state(tmp_path, seed, answer)
    # the favorites count is wrong (2) yet the \b1\b from '1 result' satisfies it
    ce.verify(str(run.dir), 'Microsoft Azure--0')  # passes — collision documented


def test_self_rejecting_answer_fails(tmp_path, seed):
    answer = ('Ignore these facts: 17 compute products. The first product is App '
              'Service: a fully managed PaaS solution, 11 section headings. The '
              'second product, Azure Container Apps, does not link to a pricing '
              'details page. Azure Virtual Machines: scalable, on-demand computing. '
              'The Kubernetes search returns 1 result. The account page shows 1 '
              'favorite.')
    run = t0_run_with_correct_state(tmp_path, seed, answer)
    expect_fail(run.dir, 'Microsoft Azure--0', 'Answer rejects its own claims')


# ------------------------------------------------------ state FAILs --

def db_with_favorite(seed: Path, dest: Path, user_id: int, slug: str,
                     mutate_seed_row: bool = False, delete_row: bool = False):
    shutil.copy2(seed, dest)
    con = sqlite3.connect(dest)
    con.execute("INSERT INTO favorites (user_id, product_slug, created_ts) "
                "VALUES (?, ?, '2026-09-30T00:00:00Z')", (user_id, slug))
    if mutate_seed_row:
        con.execute("UPDATE products SET name = 'Tampered' WHERE id = 1")
    if delete_row:
        con.execute('DELETE FROM pricing_cards WHERE id = 1')
    con.commit()
    con.close()
    return dest


# Real honest walkthrough URL sequences (the reviewer's Chromium runs for the
# r2 re-review (fix branch @ 36430fcc, port 46125 -> normalized to the task
# origin 40133)), embedded so the path-calibration and state tests grade
# against genuinely reachable evidence. T14/T19 refreshed to the rewritten
# tasks' honest paths (runs/round{1,2}/task{14,19}); T0/T1/T12/T18 are the
# same sequences the review branch calibrated against.
HONEST_URLS = {
    'Microsoft Azure--0': ['/', '/products/', '/products/?category=Compute&q=',
                           '/products/app-service/', '/products/container-apps/',
                           '/products/virtual-machines/',
                           '/products/?category=Compute&q=Kubernetes',
                           '/products/kubernetes-service/',
                           '/account/login?next=/products/kubernetes-service/', '/account/'],
    'Microsoft Azure--1': ['/', '/products/', '/products/?category=&q=database',
                           '/products/?category=Databases&q=', '/products/cosmos-db/',
                           '/pricing/details/cosmos-db/',
                           '/account/login?next=/products/cosmos-db/',
                           '/products/?category=&q=Azure+SQL', '/products/azure-sql/',
                           '/account/'],
    'Microsoft Azure--12': ['/', '/account/signup', '/account/', '/pricing/calculator/',
                           '/pricing/calculator/?service=virtual-machines', '/products/',
                           '/products/?category=&q=Functions', '/products/functions/'],
    'Microsoft Azure--14': ['/', '/search/?q=Kubernetes',
                           '/resources/cloud-computing-dictionary/what-is-kubernetes/',
                           '/customer-stories/',
                           '/customer-stories/?industry=&product=Azure+Kubernetes+Service&q=',
                           '/customer-stories/27363-microsoft-azure-kubernetes-service/',
                           '/products/', '/products/?category=&q=Kubernetes+Service',
                           '/products/kubernetes-service/',
                           '/account/login?next=/products/kubernetes-service/', '/account/'],
    'Microsoft Azure--18': ['/', '/resources/cloud-computing-dictionary/',
                           '/resources/cloud-computing-dictionary/?q=retrieval-augmented',
                           '/resources/cloud-computing-dictionary/what-is-retrieval-augmented-generation-rag/',
                           '/products/', '/products/?category=&q=Foundry',
                           '/products/ai-foundry/', '/pricing/calculator/',
                           '/pricing/calculator/?service=virtual-machines'],
    'Microsoft Azure--19': ['/', '/account/signup', '/account/', '/products/',
                           '/products/?category=Containers&q=', '/products/container-apps/',
                           '/account/login'],
}


def full_urls_for(tid: str):
    return ['http://localhost:40133' + u for u in HONEST_URLS[tid]]


def test_wrong_owner_state_fails(tmp_path, seed):
    tid = 'Microsoft Azure--0'
    after = db_with_favorite(seed, tmp_path / 'after-owner.db', 1, 'kubernetes-service')
    run = Run(tmp_path / 'wrong-owner', tid, full_urls_for(tid),
              '17 compute products, App Service, 11 headings, no pricing link, '
              'scalable on-demand computing, 1 Kubernetes result, 1 favorite.',
              seed, after)
    expect_fail(run.dir, tid, 'Incorrect new favorites row')


def test_wrong_slug_state_fails(tmp_path, seed):
    tid = 'Microsoft Azure--0'
    after = db_with_favorite(seed, tmp_path / 'after-slug.db', 2, 'functions')
    run = Run(tmp_path / 'wrong-slug', tid, full_urls_for(tid),
              '17 compute products, App Service, 11 headings, no pricing link, '
              'scalable on-demand computing, 1 Kubernetes result, 1 favorite.',
              seed, after)
    expect_fail(run.dir, tid, 'Incorrect new favorites row')


def test_unrelated_seed_edit_fails(tmp_path, seed):
    tid = 'Microsoft Azure--0'
    after = db_with_favorite(seed, tmp_path / 'after-unrelated.db', 2, 'kubernetes-service',
                             mutate_seed_row=True)
    run = Run(tmp_path / 'unrelated-edit', tid, full_urls_for(tid),
              '17 compute products, App Service, 11 headings, no pricing link, '
              'scalable on-demand computing, 1 Kubernetes result, 1 favorite.',
              seed, after)
    expect_fail(run.dir, tid, 'Incorrect products.name')


def test_unexpected_deletion_fails(tmp_path, seed):
    tid = 'Microsoft Azure--0'
    after = db_with_favorite(seed, tmp_path / 'after-del.db', 2, 'kubernetes-service',
                            delete_row=True)
    run = Run(tmp_path / 'deletion', tid, full_urls_for(tid),
              '17 compute products, App Service, 11 headings, no pricing link, '
              'scalable on-demand computing, 1 Kubernetes result, 1 favorite.',
              seed, after)
    expect_fail(run.dir, tid, 'Wrong existing rows removed from pricing_cards')


def test_stale_initial_db_fails(tmp_path, seed):
    tid = 'Microsoft Azure--0'
    stale = db_with_favorite(seed, tmp_path / 'stale.db', 2, 'kubernetes-service')
    after = db_with_favorite(seed, tmp_path / 'after2.db', 2, 'container-apps')
    run = Run(tmp_path / 'stale-initial', tid, full_urls_for(tid),
              '17 compute products, App Service, 11 headings, no pricing link, '
              'scalable on-demand computing, 1 Kubernetes result, 1 favorite.',
              stale, after)
    expect_fail(run.dir, tid, 'Initial state does not match reviewed seed')


# ------------------------------------------------------ screenshot FAILs --

def test_blank_screenshot_fails(tmp_path, seed):
    tid = 'Microsoft Azure--2'
    run = Run(tmp_path / 'blank-shot', tid,
              ['http://localhost:40133/', 'http://localhost:40133/pricing/calculator/'],
              'x', seed, screenshots='blank')
    expect_fail(run.dir, tid, 'Blank browser screenshot')


def test_corrupt_screenshot_fails(tmp_path, seed):
    """Corrupt bytes raise inside PIL; the CLI maps any exception to FAIL
    (fail-closed). Assert both the raised error and the CLI verdict."""
    tid = 'Microsoft Azure--2'
    run = Run(tmp_path / 'corrupt-shot', tid,
              ['http://localhost:40133/', 'http://localhost:40133/pricing/calculator/'],
              'x', seed, screenshots='corrupt')
    with pytest.raises(Exception):
        ce.verify(str(run.dir), tid)
    proc = subprocess.run(
        [sys.executable, str(HERE / 'verify_2.py'), '--run_dir', str(run.dir)],
        capture_output=True, text=True)
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert proc.returncode == 1 and payload['pass'] is False


# ------------------------------------------- path calibration regression --

@pytest.mark.parametrize('task_id,missing_ok', [
    ('Microsoft Azure--0', True), ('Microsoft Azure--1', True),
    ('Microsoft Azure--12', True), ('Microsoft Azure--14', True),
    ('Microsoft Azure--18', True), ('Microsoft Azure--19', True),
])
def test_paths_accept_honest_form_submissions(task_id, missing_ok):
    """Honest browsers submit the full form state (category=&q=...), and the
    natural post-action URL convention never records /account/logout."""
    joined = ' '.join(HONEST_URLS[task_id])
    for pattern in CONTRACT[task_id]['paths']:
        assert re.search(pattern, joined, re.I), \
            f'{task_id}: honest URL shape rejected by pattern {pattern!r}'


def test_t14_does_not_require_unrequested_pages():
    """Task 14 never asks to open a product page; the contract must not
    demand /products/container-apps/ evidence for it."""
    assert '/products/container-apps/' not in CONTRACT['Microsoft Azure--14']['paths']


# ----------------------------------------------- honest-shape PASS control --

def test_honest_shape_control_passes(tmp_path, seed):
    """Drive the real app (CSRF on, fresh seed) through task 2's flow, build a
    run with real URLs, real state delta, the graded answer, and generated
    screenshots; the contract must PASS. Then flip one state value and one
    claim value and assert both FAIL (zero false positives around the gate)."""
    tid = 'Microsoft Azure--2'
    tmp = tmp_path / 'control'
    tmp.mkdir()
    db = seed_db(tmp)
    from app import app as flask_app
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        csrf_page = client.get('/pricing/calculator/?service=virtual-machines')
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"',
                          csrf_page.data).group(1).decode()
        client.post('/account/login', data={
            'csrf_token': token, 'email': 'alice.chen@test.com',
            'password': 'TestPass123!'}, follow_redirects=True)
        calc = client.post('/pricing/calculator/?service=virtual-machines', data={
            'csrf_token': token, 'service': 'virtual-machines',
            'size': 'linux-d4sv5-standard', 'region': 'us-west-2',
            'quantity': '3', 'hours': '730', 'currency': 'usd'},
            follow_redirects=True)
        total = re.search(r'Estimated monthly cost \(USD\)</th><th></th><th>(\$[\d,.]+)</th>',
                          calc.data.decode())
        assert total, 'control: estimate total not rendered'
        usd = total.group(1)
        client.post('/pricing/calculator/save', data={
            'csrf_token': token, 'service': 'virtual-machines',
            'size': 'linux-d4sv5-standard', 'region': 'us-west-2',
            'quantity': '3', 'hours': '730', 'currency': 'usd',
            'name': 'Production web tier'}, follow_redirects=True)
    answer = (f'Three always-on Linux D4s v5 virtual machines in West US 2 cost '
              f'{usd} per month. Saved as Production web tier for '
              f'alice.chen@test.com; the account page lists it at {usd} per month.')
    urls = ['http://localhost:40133/',
            'http://localhost:40133/pricing/calculator/?service=virtual-machines',
            'http://localhost:40133/account/login?next=/pricing/calculator/',
            'http://localhost:40133/pricing/calculator/?service=virtual-machines',
            'http://localhost:40133/account/']
    run = Run(tmp_path / 'control-pass', tid, urls, answer, seed, db)
    result = ce.verify(str(run.dir), tid)
    assert result['pass'], result

    # same shape, wrong saved name -> state FAIL
    con = sqlite3.connect(run.dir / 'after.db')
    con.execute("UPDATE estimates SET name='Wrong name'")
    con.commit(); con.close()
    expect_fail(run.dir, tid, 'Incorrect new estimates row')

    # restore, then wrong answer -> claim FAIL
    con = sqlite3.connect(run.dir / 'after.db')
    con.execute("UPDATE estimates SET name='Production web tier'")
    con.commit(); con.close()
    traj = json.loads((run.dir / 'trajectory.json').read_text())
    traj['final_answer'] = answer.replace(usd, '$999.99')
    (run.dir / 'trajectory.json').write_text(json.dumps(traj))
    expect_fail(run.dir, tid, 'Missing or incorrect usd total')


def test_cli_exit_code_matches(tmp_path, seed):
    """The verify_N.py CLI maps FAIL to exit code 1."""
    run = noop_run(tmp_path, seed, 'Microsoft Azure--2')
    proc = subprocess.run(
        [sys.executable, str(HERE / 'verify_2.py'), '--run_dir', str(run.dir)],
        capture_output=True, text=True)
    assert proc.returncode == 1
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload['pass'] is False
