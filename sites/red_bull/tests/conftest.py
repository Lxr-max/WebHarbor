from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(tempfile.mkdtemp(prefix="red-bull-tests-"))
os.environ["RED_BULL_DB_URI"] = f"sqlite:///{TEST_ROOT / 'red_bull.db'}"
sys.path.insert(0, str(SITE_DIR))

import app as red_bull_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield
    with red_bull_app.app.app_context():
        red_bull_app.db.session.remove()
        red_bull_app.db.engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture()
def client():
    """CSRF stays ENABLED: every form post must carry the page's token."""
    red_bull_app.app.config.update(TESTING=True)
    with red_bull_app.app.test_client() as test_client:
        yield test_client


def csrf_from(html: str) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "csrf token not found on form page"
    return m.group(1)


@pytest.fixture()
def csrf():
    return csrf_from


@pytest.fixture()
def alice(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    resp = client.post("/account/login", data={
        "csrf_token": csrf(html),
        "email": "alice.j@test.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 302
    return client


@pytest.fixture()
def dana(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    resp = client.post("/account/login", data={
        "csrf_token": csrf(html),
        "email": "dana.k@test.com",
        "password": "TestPass123!",
    })
    assert resp.status_code == 302
    return client


@pytest.fixture(scope="module")
def seeded_counts():
    with red_bull_app.app.app_context():
        from flask_login import current_user  # noqa: F401
        return {
            "users": red_bull_app.User.query.count(),
            "products": red_bull_app.Product.query.count(),
            "events": red_bull_app.Event.query.count(),
            "athletes": red_bull_app.Athlete.query.count(),
            "films": red_bull_app.Film.query.count(),
            "shows": red_bull_app.Show.query.count(),
            "stories": red_bull_app.Story.query.count(),
            "shop_products": red_bull_app.ShopProduct.query.count(),
        }
