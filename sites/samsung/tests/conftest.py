"""Shared pytest fixtures: a fresh seeded database and a CSRF-enabled test
client for the samsung mirror."""
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE))


@pytest.fixture()
def client(tmp_path):
    os.environ['SAMSUNG_DB_URI'] = f'sqlite:///{tmp_path / "samsung.db"}'
    os.environ.pop('WEBSYN_SKIP_BOOTSTRAP', None)
    for mod in list(sys.modules):
        if mod.startswith(('app', 'seed')):
            del sys.modules[mod]
    import app as A
    A.app.config.update(TESTING=True)
    with A.app.test_client() as c:
        yield A, c
    shutil.rmtree(tmp_path, ignore_errors=True)


def csrf(client, url):
    r = client.get(url)
    assert r.status_code == 200, f'{url} -> {r.status_code}'
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f'no csrf token on {url}'
    return m.group(1).decode()


def login(client, email='alice.j@test.com', password='TestPass123!'):
    token = csrf(client, '/account/login/')
    return client.post('/account/login/', data={
        'email': email, 'password': password, 'csrf_token': token,
    }, follow_redirects=True)
