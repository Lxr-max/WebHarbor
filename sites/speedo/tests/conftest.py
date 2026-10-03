"""Shared pytest fixtures for the speedo mirror test suite.

Each test module gets a scratch database (a copy of instance_seed/speedo.db)
via the SPEEDO_DB_PATH hook, so stateful tests never touch the real instance
database and never break the byte-identical reset invariant.
"""
import os
import pathlib
import shutil
import sys

import re

import pytest
from flask.testing import FlaskClient


class FormClient(FlaskClient):
    """Injects a valid signed CSRF token (scraped from a rendered form) into
    every POST, mirroring what a browser does."""

    def post(self, *args, **kwargs):
        data = {**kwargs.get("data", {})}
        if "csrf_token" not in data:
            page = self.get("/pages/contact").get_data(as_text=True)
            m = re.search(r'name="csrf_token" value="([^"]+)"', page)
            if m:
                data["csrf_token"] = m.group(1)
        kwargs["data"] = data
        return super().post(*args, **kwargs)


SITE = pathlib.Path(__file__).resolve().parent.parent
SEED = pathlib.Path(os.environ["SPEEDO_TEST_SEED_DB"]) if os.environ.get("SPEEDO_TEST_SEED_DB") else SITE / "instance_seed" / "speedo.db"

if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))


@pytest.fixture()
def app(tmp_path):
    if not SEED.exists():
        pytest.skip("instance_seed/speedo.db not built yet")
    scratch = tmp_path / "speedo.db"
    shutil.copyfile(SEED, scratch)
    os.environ["SPEEDO_DB_PATH"] = f"sqlite:///{scratch}"
    try:
        import importlib
        import app as app_module
        importlib.reload(app_module)
        app_module.app.test_client_class = FormClient
        yield app_module.app
    finally:
        os.environ.pop("SPEEDO_DB_PATH", None)


@pytest.fixture()
def client(app):
    return app.test_client()
