"""Shared pytest fixtures for the student_com mirror test suite.

Each test module gets a scratch database (a copy of instance_seed/student_com.db)
via the STUDENT_COM_DB_PATH hook, so stateful tests never touch the real
instance database and never break the byte-identical reset invariant.
"""
import importlib
import os
import pathlib
import re
import shutil
import sys

import pytest

SITE = pathlib.Path(__file__).resolve().parent.parent
SEED = SITE / "instance_seed" / "student_com.db"

if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))


@pytest.fixture()
def app(tmp_path):
    if not SEED.exists():
        pytest.skip("instance_seed/student_com.db not built yet")
    scratch = tmp_path / "student_com.db"
    shutil.copyfile(SEED, scratch)
    os.environ["STUDENT_COM_DB_PATH"] = f"sqlite:///{scratch}"
    try:
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        yield app_module.app
    finally:
        os.environ.pop("STUDENT_COM_DB_PATH", None)


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_token(client):
    """Scrape the CSRF token the way the browser-side JS does."""
    page = client.get("/").get_data(as_text=True)
    m = re.search(r'window\.CSRF_TOKEN = "([^"]+)"', page)
    assert m, "no CSRF token rendered"
    return m.group(1)


def login(client, email="alice.j@test.com", pw="TestPass123!"):
    response = client.post(
        "/auth/login", data={"email": email, "password": pw},
        headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 200, response.status_code
    assert response.get_json()["ok"] is True
    return response
