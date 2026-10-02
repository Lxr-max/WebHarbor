from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="coinmarketcap-tests-"))
os.environ["COINMARKETCAP_DB_URI"] = f"sqlite:///{TEST_ROOT / 'coinmarketcap.db'}"
os.environ["COINMARKETCAP_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as cmc_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with cmc_app.app.app_context():
        cmc_app.db.session.remove()
        cmc_app.db.engine.dispose()
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
    cmc_app.app.config.update(TESTING=True)
    return cmc_app.app.test_client()


def _login(client, email, password='TestPass123!'):
    r = client.post('/login', data=with_csrf(client, '/login',
                                             {'email': email, 'password': password}))
    assert r.status_code == 302, f"login failed: {r.status_code}"
    return client


@pytest.fixture()
def alice(client):
    return _login(client, 'alice.j@test.com')
