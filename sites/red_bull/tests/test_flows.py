"""Functional flow tests: drive the mirror the way an agent would —
navigate, filter, open details, fill forms (with CSRF tokens), and verify
the DB after-state."""
from __future__ import annotations

import re

import pytest

import app as rb  # noqa: E402


def _csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m
    return m.group(1)


# ----------------------------------------------------------------- events --

def test_event_calendar_filter_and_detail_flow(client):
    resp = client.get("/events?discipline=Motocross")
    body = resp.get_data(as_text=True)
    assert "Barn Find Open" in body or "Motocross" in body
    # open a filtered event
    resp = client.get("/events/red-bull-barn-find-open")
    assert b"Oak Ridge" in resp.get_data()
    # its discipline tag matches the filter
    assert b"Motocross" in resp.get_data()


def test_event_registration_flow_with_csrf(client):
    token = _csrf(client, "/events/red-bull-foam-wreckers-virginia-beach/register")
    resp = client.post("/events/red-bull-foam-wreckers-virginia-beach/register", data={
        "csrf_token": token,
        "first_name": "Casey", "last_name": "Rider",
        "email": "casey@example.com", "ticket_type": "registration",
    })
    assert resp.status_code == 302
    m = re.search(r"/register/confirmation/(RB[A-Z0-9]+)", resp.headers["Location"])
    assert m
    code = m.group(1)
    page = client.get(f"/events/red-bull-foam-wreckers-virginia-beach/register/confirmation/{code}")
    assert b"Casey" in page.get_data()
    with rb.app.app_context():
        reg = rb.EventRegistration.query.filter_by(registration_code=code).first()
        assert reg is not None
        assert reg.price == 20


def test_event_registration_validation(client):
    token = _csrf(client, "/events/red-bull-foam-wreckers-virginia-beach/register")
    resp = client.post("/events/red-bull-foam-wreckers-virginia-beach/register", data={
        "csrf_token": token, "first_name": "", "last_name": "",
        "email": "not-an-email", "ticket_type": "",
    })
    body = resp.get_data(as_text=True)
    assert "valid email address" in body
    assert "ticket type" in body
    with rb.app.app_context():
        assert rb.EventRegistration.query.filter_by(
            email="not-an-email").count() == 0


def test_registration_requires_a_priced_event(client):
    assert client.get("/events/dtm-hockenheimring/register").status_code == 404


def test_event_series_page_lists_stops(client):
    resp = client.get("/event-series/red-bull-cliff-diving")
    body = resp.get_data(as_text=True)
    assert "Tour stops" in body
    assert "Polignano a Mare" in body or "Mostar" in body


def test_event_past_upcoming_filter(client):
    upcoming = client.get("/events?status=upcoming").get_data(as_text=True)
    assert "Foam Wreckers - Virginia Beach" in upcoming
    past = client.get("/events?status=past").get_data(as_text=True)
    assert "Foam Wreckers - Virginia Beach" not in past


# ---------------------------------------------------------------- products --

def test_products_filter_by_line(client):
    body = client.get("/energydrink?line=Red+Bull+Editions").get_data(as_text=True)
    assert "Red Bull Summer Edition" in body
    assert "The Original Red Bull" not in body


def test_product_detail_ingredients(client):
    body = client.get("/energydrink/red-bull-summer-edition").get_data(as_text=True)
    assert "80 mg" in body            # caffeine
    assert "26 g" in body              # sugars
    assert "Taurine" in body
    assert "12 fl oz" in body


def test_editions_carry_flavor_names(client):
    with rb.app.app_context():
        amber = rb.Product.query.filter_by(slug="red-bull-amber-edition").first()
        flavor = amber.flavor or ""
        assert "Strawberry" in flavor and "Apricot" in flavor
        summer = rb.Product.query.filter_by(slug="red-bull-summer-edition").first()
        assert "Sudachi" in (summer.flavor or "")


# ---------------------------------------------------------------- athletes --

def test_athlete_filters(client):
    body = client.get("/athletes?country=United+Kingdom").get_data(as_text=True)
    assert "Sky Brown" in body
    body = client.get("/athletes?letter=S").get_data(as_text=True)
    assert "Sky Brown" in body
    assert "Bjorn Riley" not in body


def test_athlete_profile_facts(client):
    body = client.get("/athletes/sky-brown").get_data(as_text=True)
    assert "July 7, 2008" in body
    assert "Miyazaki, Japan" in body
    assert "2018" in body


# -------------------------------------------------------------- films/shows --

def test_films_pagination_and_filter(client):
    body = client.get("/films").get_data(as_text=True)
    assert "9191" in body or "Films" in body
    body = client.get("/films?page=2").get_data(as_text=True)
    assert "‹ Prev" in body or "Next" in body


def test_show_episodes_listed(client):
    with rb.app.app_context():
        show = rb.Show.query.filter(rb.Show.episodes.any()).first()
        assert show
    body = client.get(f"/shows/{show.slug}").get_data(as_text=True)
    assert "S2" in body or "Season" in body


# ----------------------------------------------------------------- stories --

def test_story_detail_body(client):
    body = client.get("/stories/jreamz-wins-2026-red-bull-dance-your-style-national-final").get_data(as_text=True)
    assert "JREAMZ" in body
    assert "Tampa" in body or "Kansas City" in body


def test_stories_topic_filter(client):
    body = client.get("/stories?discipline=Games").get_data(as_text=True)
    assert "EA SPORTS FC" in body or "GTA" in body


# -------------------------------------------------------------------- shop --

def _add_to_cart(client, handle):
    page = client.get(f"/shop/{handle}").get_data(as_text=True)
    m = re.search(r'name="variant_id"[^>]*>\s*<option value="(\d+)"[^>]*>\s*([^<]+?) — \$',
                  page) or re.search(r'<option value="(\d+)"[^>]*>([^<]+?) — \$', page)
    assert m, f"no variant options on {handle}"
    variant_id, option = m.group(1), m.group(2)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
    resp = client.post("/cart/add", data={
        "csrf_token": token, "variant_id": variant_id, "quantity": 1})
    assert resp.status_code == 302
    return int(variant_id), option


def test_shop_category_and_sort_filters(client):
    body = client.get("/shop?category=headwear").get_data(as_text=True)
    assert "beanie" in body.lower() or "cap" in body.lower() or "hat" in body.lower()
    body = client.get("/shop?sort=price_asc").get_data(as_text=True)
    assert "products" in body


def test_shop_product_variants_table(client):
    with rb.app.app_context():
        product = rb.ShopProduct.query.filter(
            rb.ShopProduct.variants.any()).first()
        handle = product.handle
        sku = product.variants[0].sku
    body = client.get(f"/shop/{handle}").get_data(as_text=True)
    assert "SKU" in body
    assert sku in body


def test_cart_add_update_remove_flow(client):
    with rb.app.app_context():
        product = rb.ShopProduct.query.filter(
            rb.ShopProduct.variants.any(rb.ShopVariant.available.is_(True))).first()
        variant = next(v for v in product.variants if v.available)
    variant_id, _ = _add_to_cart(client, product.handle)
    cart = client.get("/cart").get_data(as_text=True)
    assert product.title in cart

    token = _csrf(client, "/cart")
    item_id = int(re.search(r'name="item_id" value="(\d+)"', cart).group(1))
    resp = client.post("/cart/update", data={
        "csrf_token": token, "item_id": item_id, "quantity": 3})
    assert resp.status_code == 302
    cart = client.get("/cart").get_data(as_text=True)
    assert 'value="3"' in cart

    resp = client.post("/cart/remove", data={
        "csrf_token": token, "item_id": item_id})
    assert resp.status_code == 302
    cart = client.get("/cart").get_data(as_text=True)
    assert product.title not in cart


def test_checkout_requires_login(client):
    with rb.app.app_context():
        product = rb.ShopProduct.query.filter(
            rb.ShopProduct.variants.any()).first()
    _add_to_cart(client, product.handle)
    resp = client.get("/shop/checkout")
    assert resp.status_code == 302
    assert "/account/login" in resp.headers["Location"]


def test_full_checkout_flow_places_order(alice):
    with rb.app.app_context():
        product = rb.ShopProduct.query.filter(
            rb.ShopProduct.variants.any(rb.ShopVariant.available.is_(True))).first()
        handle = product.handle
        title = product.title
        before = rb.ShopOrder.query.count()
    _add_to_cart(alice, handle)
    token = _csrf(alice, "/shop/checkout")
    resp = alice.post("/shop/checkout", data={
        "csrf_token": token, "ship_name": "Alice Johnson",
        "ship_email": "alice.j@test.com", "address": "1 Main St",
        "city": "Seattle", "zip": "98101"})
    assert resp.status_code == 302
    order_number = re.search(r"/shop/orders/(RB-\d+)",
                             resp.headers["Location"]).group(1)
    page = alice.get(f"/shop/orders/{order_number}").get_data(as_text=True)
    assert title in page
    with alice.session_transaction() as sess:
        cart_token = sess.get("cart_token")
    with rb.app.app_context():
        assert rb.ShopOrder.query.count() == before + 1
        order = rb.ShopOrder.query.filter_by(
            order_number=order_number).first()
        assert order.user_id == 1
        assert order.total > 0
        # this session's cart is emptied after checkout
        assert rb.CartItem.query.filter_by(token=cart_token).count() == 0


def test_benchmark_user_state():
    with rb.app.app_context():
        alice = rb.User.query.filter_by(email="alice.j@test.com").first()
        assert rb.ShopOrder.query.filter_by(user_id=alice.id).count() >= 1
        regs = rb.EventRegistration.query.filter_by(user_id=alice.id).all()
        assert {r.registration_code for r in regs} >= {"RB7F3A21", "RB9C04D7"}
        assert rb.Favorite.query.filter_by(user_id=alice.id).count() == 3
        dana = rb.User.query.filter_by(email="dana.k@test.com").first()
        assert rb.ShopOrder.query.filter_by(user_id=dana.id).count() == 0
        assert rb.EventRegistration.query.filter_by(
            user_id=dana.id).count() == 0
        assert rb.Favorite.query.filter_by(user_id=dana.id).count() == 0


def test_favorites_toggle_flow(alice):
    slug = "red-bull-barn-find-open"
    token = _csrf(alice, f"/events/{slug}")
    resp = alice.post("/favorites/toggle", data={
        "csrf_token": token, "kind": "event",
        "slug": slug,
        "next": f"/events/{slug}"})
    assert resp.status_code == 302
    with rb.app.app_context():
        alice_id = rb.User.query.filter_by(
            email="alice.j@test.com").first().id
        fav = rb.Favorite.query.filter_by(
            user_id=alice_id, kind="event", item_slug=slug).first()
        assert fav is not None
        # toggle again removes it
    token = _csrf(alice, f"/events/{slug}")
    alice.post("/favorites/toggle", data={
        "csrf_token": token, "kind": "event",
        "slug": slug,
        "next": f"/events/{slug}"})
    with rb.app.app_context():
        assert rb.Favorite.query.filter_by(
            user_id=alice_id, kind="event", item_slug=slug).count() == 0


def test_account_page_shows_fixture_state(alice):
    page = alice.get("/account").get_data(as_text=True)
    assert "RB7F3A21" in page
    assert "Foam Wreckers" in page
    assert "RB-100234" in page


def test_logout_flow(alice):
    token = _csrf(alice, "/account")
    resp = alice.post("/account/logout", data={"csrf_token": token})
    assert resp.status_code == 302
    page = alice.get("/account")
    assert page.status_code == 302
