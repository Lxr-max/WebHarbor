from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="verizon-tests-"))
os.environ["VERIZON_DB_URI"] = f"sqlite:///{TEST_ROOT / 'verizon.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as verizon_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with verizon_app.app.app_context():
        verizon_app.db.session.remove()
        verizon_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    """CSRF stays ENABLED: every form post must carry the page's token."""
    verizon_app.app.config.update(TESTING=True)
    with verizon_app.app.test_client() as test_client:
        yield test_client


def csrf_from(html: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "csrf token not found on form page"
    return m.group(1)


@pytest.fixture()
def csrf():
    return csrf_from


@pytest.fixture()
def alice(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    client.post("/account/login",
                data={"email": "alice.j@test.com", "password": "TestPass123!",
                      "csrf_token": csrf_from(html)},
                follow_redirects=True)
    return client


@pytest.fixture()
def bob(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    client.post("/account/login",
                data={"email": "bob.c@test.com", "password": "TestPass123!",
                      "csrf_token": csrf_from(html)},
                follow_redirects=True)
    return client


@pytest.fixture()
def carol(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    client.post("/account/login",
                data={"email": "carol.d@test.com", "password": "TestPass123!",
                      "csrf_token": csrf_from(html)},
                follow_redirects=True)
    return client


@pytest.fixture()
def dana(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    client.post("/account/login",
                data={"email": "dana.k@test.com", "password": "TestPass123!",
                      "csrf_token": csrf_from(html)},
                follow_redirects=True)
    return client

@pytest.fixture(autouse=True)
def restore_db():
    # Tests never leave state for another case.
    with verizon_app.app.app_context():
        tables = list(verizon_app.db.metadata.sorted_tables)
        rows = {t.name: [dict(r._mapping) for r in verizon_app.db.session.execute(t.select())] for t in tables}
    yield
    with verizon_app.app.app_context():
        verizon_app.db.session.remove()
        for t in reversed(tables): verizon_app.db.session.execute(t.delete())
        for t in tables:
            if rows[t.name]: verizon_app.db.session.execute(t.insert(), rows[t.name])
        verizon_app.db.session.commit()


