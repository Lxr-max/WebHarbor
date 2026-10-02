from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="stanford-university-tests-"))
os.environ["STANFORD_UNIVERSITY_DB_URI"] = f"sqlite:///{TEST_ROOT / 'stanford_university.db'}"
os.environ["STANFORD_UNIVERSITY_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as su_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with su_app.app.app_context():
        su_app.db.session.remove()
        su_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def app_context():
    with su_app.app.app_context():
        yield


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
    su_app.app.config.update(TESTING=True)
    return su_app.app.test_client()


def _login(client, email):
    data = with_csrf(client, "/login", {"email": email,
                                       "password": "TestPass123!"})
    r = client.post("/login", data=data, follow_redirects=True)
    assert r.status_code == 200
    assert b"Invalid email or password" not in r.data


def _logout(client):
    data = with_csrf(client, "/", {})
    client.post("/logout", data=data, follow_redirects=True)
