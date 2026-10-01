from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="wanderlog-tests-"))
os.environ["WANDERLOG_DB_URI"] = f"sqlite:///{TEST_ROOT / 'wanderlog.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as wanderlog_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with wanderlog_app.app.app_context():
        wanderlog_app.db.session.remove()
        wanderlog_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


def with_csrf(client, source, data):
    """Mimic a real browser: load the page that hosts the form, read the
    CSRF token out of the rendered HTML, and submit it with the form.

    CSRF protection stays ENABLED for the whole suite (the reviewer
    convention: tests must submit real tokens like a browser does)."""
    r = client.get(source)
    assert r.status_code == 200, f"token source {source} -> {r.status_code}"
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f"no csrf_token input rendered on {source}"
    out = dict(data)
    out["csrf_token"] = m.group(1).decode()
    return out


@pytest.fixture()
def client():
    # CSRF protection stays ON: tests submit real tokens like a browser.
    # (a bare test_client — the `with client:` context manager keeps request
    # contexts stacked across clients and breaks other sessions' cookies)
    wanderlog_app.app.config.update(TESTING=True)
    return wanderlog_app.app.test_client()


def _login(client, email):
    client.post('/login', data=with_csrf(client, '/login',
                                         {'email': email,
                                          'password': 'TestPass123!'}))
    return client


def _fresh_login(email):
    """A dedicated logged-in client (separate browser session)."""
    wanderlog_app.app.config.update(TESTING=True)
    client = wanderlog_app.app.test_client()
    return _login(client, email)


@pytest.fixture()
def alice():
    return _fresh_login('alice.j@test.com')


@pytest.fixture()
def bob():
    return _fresh_login('bob.c@test.com')


@pytest.fixture()
def carol():
    return _fresh_login('carol.d@test.com')


@pytest.fixture()
def dana():
    return _fresh_login('dana.k@test.com')
