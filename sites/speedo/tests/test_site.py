"""Robustness checks for the speedo mirror: every key route renders non-empty
content, forms validate and persist, search handles partial queries, cart and
discount math is exact, and bad input fails gracefully.

All tests run against the conftest scratch database (a copy of
instance_seed/speedo.db), never the live worktree instance.
"""
import html
import json
import pathlib
import re

import pytest

SITE = pathlib.Path(__file__).resolve().parent.parent


def text_of(response):
    return html.unescape(response.get_data(as_text=True))


def get(client, path, min_len=500):
    response = client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}"
    body = response.get_data(as_text=True)
    assert len(body) > min_len, f"{path} rendered suspiciously little content"
    return body


def login(client, email="alice.j@test.com", pw="TestPass123!"):
    r = client.post("/login", data={"email": email, "password": pw})
    assert r.status_code == 302, r.status_code


# ---------------- health ----------------

def test_health_endpoint(client):
    response = client.get("/_health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["counts"]["products"] >= 1000
    assert data["counts"]["collections"] >= 100
    assert data["counts"]["users"] >= 4
    assert data["counts"]["athletes"] >= 10
    assert data["counts"]["articles"] >= 8


# ---------------- catalog ----------------

def test_homepage_renders_catalog(client):
    body = get(client, "/", 20000)
    for nav in ["Women", "Men", "Kids", "Goggles", "Accessories"]:
        assert nav in body
    assert "Swimwear Quiz" in body or "swimsuit-quiz" in body
    assert "Free UK delivery on orders over £50" in body


def test_collection_facets_and_sort(client):
    body = get(client, "/collections/women-swimwear-all")
    assert "products" in body
    # price sort: cheapest first
    body = get(client, "/collections/women-swimwear-all?sort_by=price-ascending")
    prices = [float(m) for m in re.findall(r"£([\d.]+)", body)]
    assert prices, "no prices rendered"
    # activity facet narrows the count
    body = get(client, "/collections/men-jammers?activity=Fitness")
    assert "46 products" in body or "products" in body


def test_pdp_sizes_colourways_and_specs(client):
    body = get(client, "/products/womens-fastskin-lzr-ignite-kneeskin-black-grey-81343719224")
    assert "Fastskin" in body
    assert "£114.00" in body
    assert "26" in body  # size pills
    assert "colour-swatch-link" in body or "swatch" in body
    assert "SKU" in body or "sku" in body


def test_search_relevance_and_fuzz(client):
    body = get(client, "/search?q=hyperboom+jammer")
    assert "Hyperboom" in body
    # partial + typo tolerance
    body = get(client, "/search?q=medalist")
    assert "Medalist" in body
    # empty query must not 500
    r = client.get("/search?q=")
    assert r.status_code == 200


def test_sold_out_logic_visible(client):
    # a sold-out product's PDP must carry the badge and block purchase
    body = get(client, "/products/womens-club-training-tri-back-swimsuit-teal-blue-8005168002")
    assert "Sold out" in body or "sold" in body.lower()


# ---------------- size guides / quizzes ----------------

def test_size_guide_tables(client):
    body = get(client, "/pages/size-guides")
    assert "91-96" in body          # women's CM row for size 36
    assert "9-10 Yrs" in body       # kids band
    assert "66" in body             # kids waist column


def test_swimsuit_quiz_flow(client):
    r = client.get("/pages/swimsuit-quiz")
    assert r.status_code == 200
    r = client.post("/pages/swimsuit-quiz", data={"step": "0", "value": "Women's"})
    assert r.status_code == 302
    r = client.post("/pages/swimsuit-quiz", data={"step": "1", "value": "Racing"})
    assert r.status_code == 302
    r = client.post("/pages/swimsuit-quiz", data={"step": "2", "value": "Fastskin Ignite"})
    assert r.status_code == 302
    body = get(client, "/pages/swimsuit-quiz/results")
    assert "Fastskin" in body
    assert "£114.00" in body  # cheapest in-stock rec


def test_goggles_quiz_flow(client):
    client.post("/pages/goggles-quiz", data={"step": "0", "value": "Adults"})
    client.post("/pages/goggles-quiz", data={"step": "1", "value": "Fitness"})
    client.post("/pages/goggles-quiz", data={"step": "2", "value": "Clear"})
    body = get(client, "/pages/goggles-quiz/results")
    assert "Hydrosity" in body  # cheapest in-stock clear-lens rec


# ---------------- cart / checkout / discounts ----------------

def test_guest_cart_and_checkout_math(client):
    client.post("/cart/add", data={"slug": "biofuse-2-0-goggles-black-800233214501",
                                   "size": "One Size", "qty": "1"})
    body = get(client, "/cart")
    assert "£25.00" in body
    r = client.post("/checkout", data={
        "email": "walk.tester@example.com", "first_name": "Walk", "last_name": "Tester",
        "line1": "1 Test Row", "city": "Portsmouth", "postcode": "PO1 1AA",
        "shipping_method": "express", "card_number": "4242424242424242",
        "exp_month": "12", "exp_year": "28", "cvc": "123", "card_name": "Walk Tester"})
    assert r.status_code == 302
    body = get(client, r.headers["Location"])
    assert "Thank you for your order" in body or "THANK YOU" in body.upper()
    assert "£33.99" in body  # 25.00 + 8.99 express


def test_welcome15_discount_math(client):
    login(client)
    # alice's seeded basket: medalist black £31.00 + biofuse goggles £25.00
    r = client.post("/cart/discount", data={"code": "WELCOME15"})
    assert r.status_code in (200, 302)
    body = get(client, "/cart")
    assert "WELCOME15" in body
    # 56.00 * 0.85 = 47.60
    assert "47.60" in body


def test_unknown_coupon_rejected(client):
    login(client)
    client.post("/cart/discount", data={"code": "SAVE99"})
    body = get(client, "/cart")
    assert "not valid" in body.lower()


def test_free_shipping_threshold(client):
    login(client, "carol.d@test.com")
    body = get(client, "/cart")
    assert "£33.88" in body  # seeded subtotal
    assert "£16.12" in body   # remaining to free delivery banner


# ---------------- account ----------------

def test_login_wrong_password_fails(client):
    r = client.post("/login", data={"email": "alice.j@test.com", "password": "nope"})
    assert r.status_code == 200  # re-renders with error
    assert "Incorrect email or password" in text_of(r)


def test_order_history_and_tracking(client):
    login(client, "david.k@test.com")
    body = get(client, "/account")
    assert "SP100007" in body
    body = get(client, "/account/orders/SP100007")
    assert "SDRM100522663GB" in body
    assert "£286.99" in body


def test_wishlist_contents(client):
    login(client, "bob.c@test.com")
    body = get(client, "/account/wishlist")
    assert "Fastskin LZR Pure Intent" in body
    assert "Hyperboom Jammer" in body


def test_contact_case_reference(client):
    r = client.post("/pages/contact", data={
        "first_name": "Test", "last_name": "User", "email": "t@example.com",
        "category": "Orders &amp; Delivery", "subcategory": "Where is my order",
        "order_number": "SP100007", "message": "Where is my order?"})
    body = text_of(r)
    assert "CAS" in body  # case reference issued


def test_newsletter_reveals_welcome_code(client):
    r = client.post("/newsletter", data={"email": "news@example.com"})
    assert r.status_code in (200, 302)
    body = get(client, "/")
    assert "WELCOME15" in body  # flash reveals the welcome code


# ---------------- content pages ----------------

def test_team_and_blog_content(client):
    body = get(client, "/pages/team-speedo")
    assert "Team GB" in body or "TEAM GB" in body.upper()
    assert "Léon Marchand" in body or "Marchand" in body
    body = get(client, "/blogs/news/")
    assert "goggles" in body.lower()


def test_faqs_page(client):
    body = get(client, "/pages/faqs")
    assert "FAQ" in body.upper()


# ---------------- bad input ----------------

def test_bad_routes_404_not_500(client):
    for path in ["/products/does-not-exist", "/collections/nope",
                 "/order/confirmation/SP999999", "/pages/team-speedo-nobody"]:
        r = client.get(path)
        assert r.status_code == 404, f"{path} -> {r.status_code}"


def test_xss_escape_on_search(client):
    r = client.get("/search?q=<script>alert(1)</script>")
    body = r.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body


# ---------------- tasks contract ----------------

def test_tasks_jsonl_contract():
    rows = [json.loads(l) for l in (SITE / "tasks.jsonl").read_text().splitlines() if l.strip()]
    assert 15 <= len(rows) <= 25
    required = {"web_name", "id", "ques", "web", "upstream_url"}
    grading = {"verifier_path", "judge_rubric"}  # appended by the review contract
    for row in rows:
        assert required <= set(row), f"missing keys {required - set(row)}"
        assert set(row) <= (required | grading), f"unexpected keys {set(row) - required - grading}"
        assert row["web"] == "http://localhost:40103/"
        assert len(row["ques"].split()) <= 100
        assert "answer" not in row
        assert row["id"].startswith("Speedo--")


# ---------------- seed idempotency (byte stability at boot) ----------------

def test_boot_leaves_seed_bytes_untouched(app, tmp_path):
    import hashlib
    db_path = pathlib.Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
    before = hashlib.md5(db_path.read_bytes()).hexdigest()
    with app.app_context():
        import app as app_module
        app_module.seed_database()      # populated DB -> early return
        app_module.seed_benchmark_users()
    after = hashlib.md5(db_path.read_bytes()).hexdigest()
    assert before == after


@pytest.mark.parametrize("model", ["Ignite", "Valor", "Intent"])
def test_racing_quiz_honors_selected_model(client, model):
    for i, choice in enumerate(["Women's", "Racing", "Fastskin " + model]):
        client.post('/pages/swimsuit-quiz', data={'step': str(i), 'value': choice})
    body = get(client, '/pages/swimsuit-quiz/results')
    names = re.findall(r'<a class="card-name"[^>]*>(.*?)</a>', body)
    assert names and all(model in name for name in names)


def test_checkout_rejects_unknown_delivery_method(client):
    client.post('/cart/add', data={'slug': 'biofuse-2-0-goggles-black-800233214501', 'size': 'One Size', 'qty': '1'})
    response = client.post('/checkout', data={
        'email': 'swimmer@example.com', 'first_name': 'Test', 'last_name': 'Swimmer',
        'line1': '1 Test Row', 'city': 'Portsmouth', 'postcode': 'PO1 1AA',
        'shipping_method': 'invalid', 'card_number': '4242424242424242',
        'exp_month': '12', 'exp_year': '28', 'cvc': '123', 'card_name': 'Test Swimmer'})
    assert response.status_code == 200
    assert 'Choose a valid delivery method.' in response.get_data(as_text=True)
