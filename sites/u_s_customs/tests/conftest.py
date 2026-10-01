from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="us-customs-tests-"))
os.environ["US_CUSTOMS_DB_URI"] = f"sqlite:///{TEST_ROOT / 'u_s_customs.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as us_customs_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with us_customs_app.app.app_context():
        us_customs_app.db.session.remove()
        us_customs_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    us_customs_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with us_customs_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client):
    client.post('/login', data={'email': 'alice.j@test.com',
                                'password': 'TestPass123!'})
    return client
