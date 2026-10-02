"""Shared pytest fixtures for the stubhub mirror test suite.

Each test module gets a scratch database (a copy of instance_seed/stubhub.db)
via the STUBHUB_DB_PATH hook, so stateful tests never touch the real instance
database and never break the byte-identical reset invariant.
"""
import importlib
import os
import pathlib
import shutil
import sys

import pytest

SITE = pathlib.Path(__file__).resolve().parent.parent
SEED = SITE / "instance_seed" / "stubhub.db"

if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))


@pytest.fixture()
def app(tmp_path):
    if not SEED.exists():
        pytest.skip("instance_seed/stubhub.db not built yet")
    scratch = tmp_path / "stubhub.db"
    shutil.copyfile(SEED, scratch)
    os.environ["STUBHUB_DB_PATH"] = f"sqlite:///{scratch}"
    try:
        import app as app_module
        importlib.reload(app_module)
        yield app_module.app
    finally:
        os.environ.pop("STUBHUB_DB_PATH", None)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def alice(client):
    """Log in the benchmark user alice (orders + sales + listings fixtures)."""
    response = client.post("/secure/login", data={
        "email": "alice.j@test.com", "password": "TestPass123!"},
        follow_redirects=False)
    assert response.status_code == 302
    return client
