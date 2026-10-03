from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="tumblr-tests-"))
os.environ["TUMBLR_DB_URI"] = f"sqlite:///{TEST_ROOT / 'tumblr.db'}"
os.environ["WEBSYN_SKIP_BOOTSTRAP"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as tumblr_app  # noqa: E402


with tumblr_app.app.app_context():
    tumblr_app.create_schema()
    tumblr_app.seed_database()
    tumblr_app.seed_benchmark_users()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with tumblr_app.app.app_context():
        tumblr_app.db.session.remove()
        tumblr_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    tumblr_app.app.config.update(TESTING=True)
    with tumblr_app.app.test_client() as test_client:
        yield test_client


def login(client, email, password="TestPass123!"):
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=True)


@pytest.fixture()
def alice(client):
    login(client, "alice.j@test.com")
    return client


@pytest.fixture()
def bob(client):
    login(client, "bob.c@test.com")
    return client


@pytest.fixture()
def carol(client):
    login(client, "carol.d@test.com")
    return client


@pytest.fixture()
def david(client):
    login(client, "david.k@test.com")
    return client
