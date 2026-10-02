from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="uscis-tests-"))
os.environ["USCIS_DB_URI"] = f"sqlite:///{TEST_ROOT / 'uscis.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as uscis_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with uscis_app.app.app_context():
        uscis_app.db.session.remove()
        uscis_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    uscis_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with uscis_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def auth_alice(client):
    client.post('/account/login', data={'email': 'alice.j@test.com',
                                        'password': 'TestPass123!'})
    return client


@pytest.fixture()
def auth_dana(client):
    client.post('/account/login', data={'email': 'dana.k@test.com',
                                        'password': 'TestPass123!'})
    return client
