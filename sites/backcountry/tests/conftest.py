from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="backcountry-tests-"))
os.environ["BACKCOUNTRY_DB_URI"] = f"sqlite:///{TEST_ROOT / 'backcountry.db'}"
os.environ["BACKCOUNTRY_AUTO_SEED"] = "1"
sys.path.insert(0, str(SITE_DIR))

import app as bc_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with bc_app.app.app_context():
        bc_app.db.session.remove()
        bc_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


def with_csrf(client, source, data):
    """Mimic a real browser: load the page that hosts the form, read the
    CSRF token out of the rendered HTML, and submit it with the form.

    CSRF protection stays ENABLED for the whole suite (the reviewer
    convention: tests must submit real tokens like a browser does)."""
    r = client.get(source)
    assert r.status_code == 200, f"token source {source} -> {r.status_code}"
    m = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', r.data)
    assert m, f"no csrf_token input rendered on {source}"
    out = dict(data)
    out["csrf_token"] = m.group(1).decode()
    return out


@pytest.fixture()
def client():
    # CSRF protection stays ON: tests submit real tokens like a browser.
    bc_app.app.config.update(TESTING=True)
    return bc_app.app.test_client()


def _login(client, email):
    r = client.post('/login',
                    data=with_csrf(client, '/login',
                                   {'email': email,
                                    'password': 'TestPass123!',
                                    'mode': 'login'}))
    assert r.status_code == 302, f"login failed: {r.status_code}"
    return client


def _fresh_login(email):
    """A dedicated logged-in client (separate browser session)."""
    bc_app.app.config.update(TESTING=True)
    client = bc_app.app.test_client()
    return _login(client, email)


@pytest.fixture()
def alice():
    return _fresh_login('alice.j@test.com')


@pytest.fixture()
def bob():
    return _fresh_login('bob.c@test.com')


@pytest.fixture()
def carol():
    return _fresh_login('carol.d@test.com')


@pytest.fixture()
def dana():
    return _fresh_login('dana.k@test.com')


def any_product_with_size():
    """A deterministic product + sku pair used by cart flows."""
    with bc_app.app.app_context():
        sku = (bc_app.ProductSku.query
               .filter(bc_app.ProductSku.status == 'InStock')
               .join(bc_app.Product)
               .order_by(bc_app.Product.id, bc_app.ProductSku.id).first())
        return sku.product.slug, sku.id
