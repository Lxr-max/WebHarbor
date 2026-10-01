from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="tourradar-tests-"))
os.environ["TOURRADAR_DB_URI"] = f"sqlite:///{TEST_ROOT / 'tourradar.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as tourradar_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with tourradar_app.app.app_context():
        tourradar_app.db.session.remove()
        tourradar_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    tourradar_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with tourradar_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def auth_client(client):
    client.post('/login', data={'email': 'alice.j@test.com',
                                'password': 'TestPass123!'})
    return client
