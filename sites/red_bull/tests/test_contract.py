"""Contract tests: every route renders, CSRF is enforced everywhere a
form posts, the seed counts match the source snapshots, and the seed is
idempotent + byte-reproducible."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from conftest import SITE_DIR, TEST_ROOT

import app as rb  # noqa: E402


def test_health_counts(client):
    data = client.get("/_health").get_json()
    assert data["ok"] is True
    assert data["products"] == 18
    assert data["events"] >= 95
    assert data["event_series"] == 5
    assert data["athletes"] >= 55
    assert data["films"] >= 95
    assert data["shows"] >= 95
    assert data["stories"] == 40
    assert data["shop_products"] >= 150
    assert data["users"] == 4
    assert data["shop_orders"] >= 1
    assert data["event_registrations"] >= 2
    assert data["favorites"] >= 8


def test_events_registration_fees_real(client):
    """The ticketed events carry their real captured entry fees."""
    with rb.app.app_context():
        priced = rb.Event.query.filter(rb.Event.reg_price.isnot(None)).all()
        assert len(priced) >= 3
        by_slug = {e.slug: e for e in priced}
        assert by_slug["red-bull-foam-wreckers-virginia-beach"].reg_price == 20
        assert by_slug["sypher-showdown"].reg_price == 15
        assert by_slug["foam-wreckers-carolina-beach"].reg_price == 10


PAGE_MARKERS = [
    ("/", [b"Energy Drinks", b"Events"]),
    ("/energydrink", [b"Red Bull Editions", b"Sudachi"]),
    ("/energydrink?line=Red+Bull+Zero", [b"Red Bull Zero"]),
    ("/energydrink/red-bull-summer-edition", [b"Sudachi Lime", b"80 mg"]),
    ("/energydrink/red-bull-energy-drink", [b"8.4 fl oz", b"16 fl oz"]),
    ("/events", [b"Red Bull Events", b"Filter"]),
    ("/events?discipline=Motocross", [b"Filter"]),
    ("/events/red-bull-foam-wreckers-virginia-beach", [b"Foam Wreckers", b"Register Now!"]),
    ("/events/red-bull-foam-wreckers-virginia-beach/faqs", [b"soft-boards"]),
    ("/events/red-bull-foam-wreckers-virginia-beach/schedule", [b"Check In"]),
    ("/events/red-bull-foam-wreckers-virginia-beach/register", [b"Complete registration"]),
    ("/events/red-bull-wings-cup-united-states-2026", [b"launching soon"]),
    ("/events/red-bull-wings-cup-united-states-2026/faqs", [b"Is there an entry fee?"]),
    ("/event-series/red-bull-cliff-diving", [b"Cliff Diving", b"Tour stops"]),
    ("/athletes", [b"Red Bull Athletes"]),
    ("/athletes/sky-brown", [b"Miyazaki", b"July 7, 2008"]),
    ("/films", [b"Red Bull Films"]),
    ("/shows", [b"Red Bull TV Shows"]),
    ("/stories", [b"Red Bull Stories"]),
    ("/shop", [b"Red Bull Shop"]),
    ("/cart", [b"Your cart"]),
    ("/account/login", [b"Log in to your Red Bull account"]),
]


@pytest.mark.parametrize("path,markers", PAGE_MARKERS)
def test_pages_render(client, path, markers):
    resp = client.get(path)
    assert resp.status_code == 200
    body = resp.get_data()
    for marker in markers:
        assert marker in body, f"{path}: missing {marker!r}"


def test_unknown_slugs_404(client):
    assert client.get("/energydrink/not-a-product").status_code == 404
    assert client.get("/events/not-an-event").status_code == 404
    assert client.get("/athletes/not-an-athlete").status_code == 404
    assert client.get("/films/not-a-film").status_code == 404
    assert client.get("/shop/not-a-product").status_code == 404
    assert client.get("/stories/not-a-story").status_code == 404
    assert client.get("/shows/not-a-show").status_code == 404


def test_csrf_enforced_on_every_post_route(client):
    """All state-changing endpoints reject a tokenless post with 400."""
    posts = [
        ("/events/red-bull-foam-wreckers-virginia-beach/register",
         {"first_name": "A", "last_name": "B", "email": "a@b.co", "ticket_type": "registration"}),
        ("/cart/add", {"variant_id": 1, "quantity": 1}),
        ("/cart/update", {"item_id": 1, "quantity": 2}),
        ("/cart/remove", {"item_id": 1}),
        ("/account/login", {"email": "alice.j@test.com", "password": "TestPass123!"}),
        ("/favorites/toggle", {"kind": "event", "slug": "x"}),
    ]
    for path, data in posts:
        resp = client.post(path, data=data)
        assert resp.status_code == 400, f"{path} accepted a tokenless post"


def test_login_requires_valid_credentials(client, csrf):
    html = client.get("/account/login").get_data(as_text=True)
    resp = client.post("/account/login", data={
        "csrf_token": csrf(html), "email": "alice.j@test.com",
        "password": "WrongPassword!"})
    assert b"Invalid email or password" in resp.get_data()


def test_seed_idempotent_and_byte_reproducible(tmp_path):
    """Re-running the seed path on a fresh DB must produce a
    byte-identical SQLite file (the /reset contract)."""
    import os
    import subprocess
    import sys

    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"
    env = dict(os.environ, PYTHONHASHSEED="0",
               RED_BULL_DB_URI=f"sqlite:///{db1}")
    subprocess.run([sys.executable, str(SITE_DIR / "seed_data.py")],
                   env=env, check=True, capture_output=True, cwd=str(SITE_DIR))
    # second run against the same file: must be a no-op (idempotent)
    subprocess.run([sys.executable, str(SITE_DIR / "seed_data.py")],
                   env=env, check=True, capture_output=True, cwd=str(SITE_DIR))
    env2 = dict(env, RED_BULL_DB_URI=f"sqlite:///{db2}")
    subprocess.run([sys.executable, str(SITE_DIR / "seed_data.py")],
                   env=env2, check=True, capture_output=True, cwd=str(SITE_DIR))
    h1 = _sqlite_digest(db1)
    h2 = _sqlite_digest(db2)
    assert h1 == h2, "two fresh seeds differ"


def _sqlite_digest(path: Path) -> str:
    import hashlib
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    digest = hashlib.sha256()
    for name, sql in rows:
        digest.update(name.encode())
        digest.update((sql or "").encode())
        for row in conn.execute(f'SELECT * FROM "{name}" ORDER BY 1, 2'):
            digest.update(repr(row).encode())
    conn.close()
    return digest.hexdigest()


def test_source_data_matches_seed():
    """The seed must carry the upstream snapshot counts."""
    with rb.app.app_context():
        events = json.loads((SITE_DIR / "source_data" / "events.json").read_text())
        assert rb.Event.query.count() == events["count"]
        faqs = sum(len(e.get("faqs", [])) for e in events["events"])
        assert rb.EventFaq.query.count() == faqs
        schedule = sum(len(e.get("schedule", [])) for e in events["events"])
        assert rb.EventScheduleItem.query.count() == schedule
        products = json.loads((SITE_DIR / "source_data" / "products.json").read_text())
        assert rb.Product.query.count() == products["count"] == 18


def test_images_are_referenced_from_static():
    """Every seeded image path must point inside static/images/ and the
    file must exist on disk (the asset bundle ships it)."""
    with rb.app.app_context():
        import os
        missing = []
        for e in rb.Event.query.all():
            for attr in ("image", "hero_image"):
                p = getattr(e, attr)
                if p and p.startswith("/static/"):
                    rel = str(SITE_DIR) + p
                    if not os.path.exists(rel):
                        missing.append(p)
        for a in rb.Athlete.query.limit(20):
            if a.hero_image and a.hero_image.startswith("/static/"):
                if not os.path.exists(str(SITE_DIR) + a.hero_image):
                    missing.append(a.hero_image)
        assert not missing, missing[:5]


# --------------------------------------------------- review-fix contracts --

def test_event_detail_renders_standfirst(client):
    """The Info tab must render event.standfirst as the lead paragraph, so
    facts that upstream publishes only in the standfirst stay answerable
    (review fix: standfirst was never rendered on event pages)."""
    body = client.get("/events/red-bull-barn-find-open").get_data(as_text=True)
    assert "90’s and early 2000’s" in body
    body = client.get("/events/red-bull-stuttgart-cerro-abajo").get_data(as_text=True)
    assert "steep staircases" in body
    body = client.get("/events/red-bull-wings-cup-united-states-2026").get_data(as_text=True)
    assert "Play EA SPORTS FC™ 27 like never before!" in body


def test_wings_cup_serves_description_and_faqs(client):
    """The Wings Cup event must carry its real upstream Overview description
    and FAQ section (review fix: description was empty, FAQs missing)."""
    body = client.get("/events/red-bull-wings-cup-united-states-2026").get_data(as_text=True)
    assert "Red Bull Wings Cup is launching soon!" in body
    assert 'href="/events/red-bull-wings-cup-united-states-2026/faqs"' in body
    faqs = client.get("/events/red-bull-wings-cup-united-states-2026/faqs").get_data(as_text=True)
    assert "What is Red Bull Wings Cup?" in faqs
    assert "Is there an entry fee?" in faqs
    assert "There is no entry fee to participate in Red Bull Wings Cup." in faqs


def test_summer_edition_sugarfree_carries_suffix(client):
    """The sugarfree Summer Edition must be named distinctly from the regular
    one (review fix: both cards were named 'Red Bull Summer Edition')."""
    body = client.get("/energydrink").get_data(as_text=True)
    assert body.count(">Red Bull Summer Edition<") == 1
    assert ">Red Bull Summer Edition Sugarfree<" in body
    page = client.get("/energydrink/red-bull-summer-edition-sugarfree").get_data(as_text=True)
    assert "<h1 class=\"page-title\">Red Bull Summer Edition Sugarfree</h1>" in page
    with rb.app.app_context():
        sf = rb.Product.query.filter_by(slug="red-bull-summer-edition-sugarfree").first()
        assert sf.name == "Red Bull Summer Edition Sugarfree"


def test_registration_form_relies_on_server_validation(client):
    """No HTML5 required/type=email on the registration form: the server-side
    error copy must be reachable through an honest browser interaction
    (review fix: native validation masked the server errors)."""
    html = client.get("/events/red-bull-foam-wreckers-virginia-beach/register").get_data(as_text=True)
    assert "required" not in html
    assert 'type="email"' not in html
    # the server-side copy is still produced (and now reachable)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    resp = client.post("/events/red-bull-foam-wreckers-virginia-beach/register", data={
        "csrf_token": token, "first_name": "", "last_name": "",
        "email": "not-an-email", "ticket_type": ""})
    body = resp.get_data(as_text=True)
    assert "Please provide both a first and last name." in body
    assert "Please provide a valid email address." in body
