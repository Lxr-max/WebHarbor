from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="airbnb-tests-"))
os.environ["AIRBNB_DB_URI"] = f"sqlite:///{TEST_ROOT / 'airbnb.db'}"
os.environ["AIRBNB_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as ab_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with ab_app.app.app_context():
        ab_app.db.session.remove()
        ab_app.db.engine.dispose()
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
    ab_app.app.config.update(TESTING=True)
    return ab_app.app.test_client()


@pytest.fixture()
def auth_client(client):
    """Alice's logged-in session."""
    r = client.post('/login', data=with_csrf(client, '/login', {
        'email': 'alice.j@test.com', 'password': 'TestPass123!'}))
    assert r.status_code in (302, 303)
    return client
