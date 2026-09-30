"""Contract tests: tasks.jsonl shape, page smoke, catalog integrity."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import app as bc_app

SITE = Path(__file__).resolve().parents[1]
TASKS = SITE / "tasks.jsonl"


# ---------------------------------------------------------------- tasks --

def test_tasks_file_exists_and_rows():
    assert TASKS.is_file()
    rows = [json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()]
    assert 15 <= len(rows) <= 25, f"task count {len(rows)} outside 15..25"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), "duplicate task ids"


def test_tasks_seven_keys_and_ports():
    rows = [json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()]
    for r in rows:
        assert set(r.keys()) >= {"web_name", "id", "ques", "web",
                                "upstream_url", "verifier_path",
                                "judge_rubric"}, r.get("id")
        assert r["web"] == "http://localhost:40138/", r["id"]
        assert r["upstream_url"] == "https://www.backcountry.com/"
        assert r["web_name"] == "Backcountry"
        assert r["verifier_path"].startswith("sites/backcountry/verify/")
        assert re.match(r"^Backcountry--\d+$", r["id"])
        assert 20 <= len(r["ques"].split()) <= 100, f"task {r['id']} word count"


def test_tasks_no_answer_leakage():
    rows = [json.loads(l) for l in TASKS.read_text().splitlines() if l.strip()]
    joined = "\n".join(r["ques"] for r in rows)
    # the questions must not leak answers with verbatim numbers/urls
    assert "40138" not in joined
    assert "http://localhost" not in joined
    assert "order number is" not in joined.lower()
    # no direct DB / source-code answers
    assert ".db" not in joined
    assert "SELECT " not in joined


# ------------------------------------------------------------ page smoke --

CORE_ROUTES = ["/", "/cart", "/login", "/register", "/shop-all-brands",
               "/search?q=tent", "/search?q=", "/info/shipping-policy",
               "/info/return-policy", "/info/loyalty", "/definitely-missing"]


@pytest.mark.parametrize("route", CORE_ROUTES)
def test_core_routes_render(client, route):
    r = client.get(route)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert len(r.data) > 2500
        assert b"Backcountry" in r.data


def test_category_pages_render(client):
    with bc_app.app.app_context():
        cats = bc_app.Category.query.order_by(bc_app.Category.id).all()
    assert cats, "no categories seeded"
    for cat in cats:
        r = client.get(f"/cat/{cat.slug}")
        assert r.status_code == 200
        from markupsafe import escape as _esc
        assert str(_esc(cat.name)).encode() in r.data
        assert f"{cat.upstream_total}</strong> products upstream".encode() in r.data


def test_brand_pages_render(client):
    with bc_app.app.app_context():
        brands = (bc_app.Brand.query.filter_by(listed=True)
                  .order_by(bc_app.Brand.id).all())
    assert brands, "no listed brands seeded"
    for b in brands:
        r = client.get(f"/brand/{b.slug}")
        assert r.status_code == 200, b.slug
        assert b.name.encode() in r.data


def test_product_pages_render(client):
    with bc_app.app.app_context():
        prods = bc_app.Product.query.order_by(bc_app.Product.id).limit(12).all()
    assert prods
    for p in prods:
        r = client.get(f"/{p.slug}")
        assert r.status_code == 200, p.slug
        escaped = (p.title.replace('&', '&amp;').replace("'", '&#39;')
                   .replace('"', '&#34;'))
        assert escaped.encode() in r.data
        assert f"Item #{p.id}".encode() in r.data


# --------------------------------------------------------- catalog rules --

def test_grid_prices_are_consistent(client):
    """Every card price on a sorted grid matches the product's stored price."""
    with bc_app.app.app_context():
        rows = (bc_app.CategoryProduct.query
                .filter_by(category_id=bc_app.Category.query
                           .filter_by(slug='ski').first().id)
                .order_by(bc_app.CategoryProduct.position).all())
        expected = [r.product.min_sale for r in rows]
    r = client.get("/cat/ski?sort=price")
    shown = re.findall(rb'class="sale">\$(\d[\d,]*)\.\d\d', r.data)
    assert shown
    got = [int(s.replace(b",", b"")) for s in shown]  # dollars on the page
    want = sorted(e // 100 for e in expected)[:len(got)]
    assert got == want


def test_sort_price_low_to_high(client):
    r = client.get("/cat/hike-camp?sort=price")
    prices = [int(x.replace(",", "")) for x in
              re.findall(r'class="sale">\$(\d[\d,]*)\.\d\d', r.data.decode())]
    assert prices == sorted(prices)


def test_sort_price_high_to_low(client):
    r = client.get("/cat/hike-camp?sort=-price")
    prices = [int(x.replace(",", "")) for x in
              re.findall(r'class="sale">\$(\d[\d,]*)\.\d\d', r.data.decode())]
    assert prices == sorted(prices, reverse=True)


def test_color_filter_path_filters(client):
    with bc_app.app.app_context():
        cat = bc_app.Category.query.filter_by(slug='ski').first()
        prods = [cp.product for cp in cat.products]
        black_ids = {p.id for p in prods
                     if any(s.color_family == 'black' for s in p.skus)}
    r = client.get("/cat/ski/color/black")
    body = r.data.decode()
    # every grid card title that renders belongs to a black product, and
    # every black product in the snapshot grid is rendered
    shown_titles = re.findall(r'class="card-title"><a href="/[a-z0-9\-.]+">([^<]+)</a>', body)
    assert shown_titles
    with bc_app.app.app_context():
        for p in (bc_app.Product.query
                  .filter(bc_app.Product.id.in_(black_ids)).all()):
            title = p.title.replace('&', '&amp;').replace("'", '&#39;')
            assert title in shown_titles, f"{p.id} missing from black grid"


def test_brand_facet_filter(client):
    with bc_app.app.app_context():
        brand = (bc_app.Brand.query
                 .filter(bc_app.BrandProduct.product_id.isnot(None))
                 .order_by(bc_app.Brand.id).first())
    r = client.get(f"/cat/hike-camp?brand={brand.name.replace(' ', '+')}")
    assert r.status_code == 200
    assert brand.name.encode() in r.data


def test_search_snapshot_upstream_total(client):
    with bc_app.app.app_context():
        snap = bc_app.SearchSnapshot.query.filter_by(term='tent').first()
    assert snap, "tent snapshot missing"
    r = client.get("/search?q=tent")
    assert f"<strong>{snap.upstream_total}</strong> products upstream".encode() in r.data


def test_review_wall_and_histogram(client):
    with bc_app.app.app_context():
        p = (bc_app.Product.query
             .filter(bc_app.Product.review_count > 20)
             .order_by(bc_app.Product.id).first())
        assert p, "no product with >20 reviews seeded"
        hist = json.loads(p.review_histogram or "[]")
    r = client.get(f"/{p.slug}")
    body = r.data.decode()
    assert "based on" in body
    total = sum(h["count"] for h in hist)
    assert f"based on {total} ratings" in body
    # individual seeded reviews render
    with bc_app.app.app_context():
        rev = bc_app.Review.query.filter_by(product_id=p.id, is_seed=True).first()
    assert rev.title.encode() in r.data or rev.text[:40].encode() in r.data


def test_question_answer_renders(client):
    with bc_app.app.app_context():
        q = bc_app.Question.query.filter(
            bc_app.Question.answers.any()).order_by(bc_app.Question.id).first()
        assert q, "no Q&A with answers seeded"
        p = bc_app.Product.query.get(q.product_id)
        q_text = q.text[:30]
        a_text = q.answers[0].text[:30]
        slug = p.slug
    r = client.get(f"/{slug}")
    assert q_text.encode() in r.data
    assert a_text.encode() in r.data


def test_benchmark_users_seeded(alice, bob, carol, dana):
    for fixture in (alice, bob, carol, dana):
        r = fixture.get("/account")
        assert r.status_code == 200
        assert b"Your Orders" in r.data


def test_info_pages_upstream_copy(client):
    r = client.get("/info/shipping-policy")
    assert r.status_code == 200
    assert b"Orders placed before 3pm MST" in r.data
    r = client.get("/info/return-policy")
    assert r.status_code == 200
    r = client.get("/info/loyalty")
    assert r.status_code == 200
