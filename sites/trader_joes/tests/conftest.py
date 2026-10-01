from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="trader-joes-tests-"))
os.environ["TRADER_JOES_DB_URI"] = f"sqlite:///{TEST_ROOT / 'trader_joes.db'}"
os.environ["TRADER_JOES_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as tj_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with tj_app.app.app_context():
        tj_app.db.session.remove()
        tj_app.db.engine.dispose()
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
    tj_app.app.config.update(TESTING=True)
    return tj_app.app.test_client()


def fresh_client():
    tj_app.app.config.update(TESTING=True)
    return tj_app.app.test_client()


def login(client, email, password="TestPass123!"):
    data = with_csrf(client, "/login", {"email": email, "password": password})
    r = client.post("/login", data=data)
    assert r.status_code in (302, 303)
    return client


@pytest.fixture()
def fresh_user_client(client):
    """A brand-new account created through the real signup form."""
    c = fresh_client()
    data = with_csrf(c, "/signup", {
        "name": "Fresh User", "email": "fresh.user@test.com",
        "password": "Password99!"})
    r = c.post("/signup", data=data)
    assert r.status_code in (302, 303)
    return c


@pytest.fixture()
def alice_client(client):
    # Each benchmark user gets an independent browser session.
    return login(fresh_client(), "alice.j@test.com")


@pytest.fixture()
def bob_client(client):
    return login(fresh_client(), "bob.c@test.com")


@pytest.fixture()
def carol_client(client):
    return login(fresh_client(), "carol.d@test.com")


@pytest.fixture()
def dana_client(client):
    return login(fresh_client(), "dana.k@test.com")
