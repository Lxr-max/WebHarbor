from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="vadm-tests-"))
os.environ["VADMV_DB_URI"] = f"sqlite:///{TEST_ROOT / 'virginia_dmv.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as vadm_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with vadm_app.app.app_context():
        vadm_app.db.session.remove()
        vadm_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


def with_csrf(client, source, data):
    """Mimic a real browser: load the page that hosts the form, read the
    CSRF token out of the rendered HTML, and submit it with the form.

    CSRF protection stays ENABLED for the whole suite: the tests submit
    real tokens exactly like a browser does.
    """
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
    vadm_app.app.config.update(TESTING=True)
    with vadm_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def alice(client):
    client.post("/account/login", data=with_csrf(client, "/account/login",
                                                  {"email": "alice.j@test.com",
                                                   "password": "TestPass123!"}))
    return client


@pytest.fixture()
def bob(client):
    client.post("/account/login", data=with_csrf(client, "/account/login",
                                                 {"email": "bob.c@test.com",
                                                  "password": "TestPass123!"}))
    return client


@pytest.fixture()
def carol(client):
    client.post("/account/login", data=with_csrf(client, "/account/login",
                                                  {"email": "carol.d@test.com",
                                                   "password": "TestPass123!"}))
    return client


@pytest.fixture()
def dana(client):
    client.post("/account/login", data=with_csrf(client, "/account/login",
                                                  {"email": "dana.k@test.com",
                                                   "password": "TestPass123!"}))
    return client
