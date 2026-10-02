from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="us_appliance-tests-"))
os.environ["US_APPLIANCE_DB_URI"] = f"sqlite:///{TEST_ROOT / 'us_appliance.db'}"
os.environ["WEBSYN_SKIP_BOOTSTRAP"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as us_app  # noqa: E402


with us_app.app.app_context():
    us_app.create_schema()
    us_app.seed_database()
    us_app.seed_benchmark_users()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with us_app.app.app_context():
        us_app.db.session.remove()
        us_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    # Flow fixtures follow the repo-wide convention (u_s_customs etc.):
    # CSRF is validated by its own contract tests with an enforcement-enabled
    # client; the journey tests drive forms without re-fetching tokens.
    us_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with us_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def csrf_client():
    """Client with CSRF enforcement ON (production behavior)."""
    us_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    with us_app.app.test_client() as test_client:
        yield test_client
    us_app.app.config.update(WTF_CSRF_ENABLED=False)


def login(client, email, password="TestPass123!"):
    return client.post("/login.php", data={"email": email, "password": password},
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
