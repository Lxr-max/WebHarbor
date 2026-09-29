"""Shared pytest fixtures for the spothero mirror test suite.

Each test module gets a scratch database (a copy of instance_seed/spothero.db)
via the SPOTHERO_DB_PATH hook, so stateful tests never touch the real
instance database and never break the byte-identical reset invariant.
"""
import importlib
import os
import pathlib
import re
import shutil
import sys

import pytest
from flask.testing import FlaskClient


TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


class FormClient(FlaskClient):
    """Test client that lifts the rendered CSRF token into every POST."""

    def post(self, *args, **kwargs):
        # scrape the signed token a rendered form emitted (what the browser
        # would submit). Anonymous sessions use the login form; authed sessions
        # fall through to the payment-methods form.
        m = TOKEN_RE.search(self.get('/auth/login').get_data(as_text=True))
        if not m:
            m = TOKEN_RE.search(
                self.get('/account/payment-methods').get_data(as_text=True))
        kwargs['data'] = {**kwargs.get('data', {}),
                          'csrf_token': m.group(1) if m else ''}
        return super().post(*args, **kwargs)


SITE = pathlib.Path(__file__).resolve().parent.parent
SEED = SITE / 'instance_seed' / 'spothero.db'

if str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))


@pytest.fixture()
def app(tmp_path):
    if not SEED.exists():
        pytest.skip('instance_seed/spothero.db not built yet')
    scratch = tmp_path / 'spothero.db'
    shutil.copyfile(SEED, scratch)
    os.environ['SPOTHERO_DB_PATH'] = f'sqlite:///{scratch}'
    try:
        import app as app_module
        importlib.reload(app_module)
        app_module.app.test_client_class = FormClient
        yield app_module.app
    finally:
        os.environ.pop('SPOTHERO_DB_PATH', None)
        sys.modules.pop('app', None)


@pytest.fixture()
def client(app):
    return app.test_client()


def login(app, email):
    """Log a benchmark user in and return the authed client."""
    client = app.test_client()
    response = client.post('/auth/login',
                           data={'email': email, 'password': 'TestPass123!'})
    assert response.status_code in (302, 303), 'login should redirect'
    return client
