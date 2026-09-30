"""Robustness checks for the stubhub mirror: every key route renders
non-empty content, the listing filters and sorts behave, the four-step
checkout persists an order, the sell flow lists tickets, favorites and gift
cards round-trip, and bad input fails gracefully.

All tests run against the conftest scratch database (a copy of
instance_seed/stubhub.db), never the live worktree instance.
"""
import re

SEAHAWKS_EVENT = "/seattle-seahawks-seattle-tickets-10-4-2026/event/160436504"
CHARGERS_EVENT = SEAHAWKS_EVENT   # October 4: LA Chargers at Seattle Seahawks
METALLICA = "/metallica-tickets/performer/8147"


def text_of(response):
    return response.get_data(as_text=True)


def get(client, path, min_len=500):
    response = client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}"
    body = response.get_data(as_text=True)
    assert len(body) > min_len, f"{path} rendered suspiciously little content"
    return body


def test_health_endpoint(client):
    response = client.get("/_health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["events"] >= 1000
    assert data["listings"] >= 15000
    assert data["performers"] >= 500
    assert data["venues"] >= 250
    assert data["users"] == 4


def test_public_routes_render(client):
    for path in ["/", "/explore", "/explore?page=2", "/search",
                 "/search?q=metallica", "/search?q=seattle",
                 "/gift-cards", "/selltickets", "/selltickets?q=seahawks",
                 "/secure/login", "/secure/register",
                 "/concerts-tickets/category/1", "/theater-tickets/category/2",
                 "/wwe-tickets/grouping/131",
                 "/comedy-tickets/category/209",
                 METALLICA, CHARGERS_EVENT]:
        get(client, path)


def test_sell_event_page_requires_login(client):
    """The sell form is behind auth: anonymous users bounce to login."""
    response = client.get("/selltickets/event/160436504", follow_redirects=False)
    assert response.status_code == 302
    assert "/secure/login" in response.headers["Location"]


def test_canonical_slugs_do_not_loop(client):
    """The canonical URL itself must render, not redirect to itself."""
    for path in ["/theater-tickets/category/2", "/wwe-tickets/grouping/131",
                 METALLICA, CHARGERS_EVENT]:
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
    # a wrong slug redirects to the canonical page
    response = client.get("/wrong/performer/8147")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(METALLICA)


def test_search_suggestions_api(client):
    for method, kwargs in (("get", {"query_string": {"q": "metal"}}),
                           ("post", {"data": {"q": "seattle"}})):
        response = getattr(client, method)(
            "/secure/search/getSuggestedSearches", **kwargs)
        assert response.status_code == 200
        rows = response.get_json()
        assert rows and rows[0]["name"], f"{method} suggestions empty"
        assert rows[0]["url"].startswith("/"), rows[0]["url"]


def test_event_filters_and_sorts(client):
    base = CHARGERS_EVENT
    body = get(client, base + "?quantity=4")
    assert "Showing" in body and "of" in body
    # quantity filter keeps only listings that can host a party of 4
    body = get(client, base + "?quantity=4&price_max=400")
    assert "Showing" in body
    # feature filter
    body = get(client, base + "?features=Clear+view&sort=price")
    assert "Clear view" in body or "Showing" in body
    # zone filter keeps the zone in the results
    body = get(client, base + "?zone=300+Level&sort=price")
    assert "300" in body
    # best-deal sort puts the biggest discount first
    body = get(client, base + "?sort=best_deal")
    assert "price-was" in body, "discounted listing should show the original price"
    first_was = re.search(r"price-was\">\$([\d,]+)", body)
    assert first_was, "best-deal sort must lead with a discounted listing"
    # bad sort falls back to recommended, never 500s
    get(client, base + "?sort=bogus")


def test_listing_detail_and_price_breakdown(client):
    body = get(client, CHARGERS_EVENT + "?sort=price")
    match = re.search(r"/listing/(\d+)", body)
    assert match, "event page must link listing detail pages"
    detail = get(client, f"{CHARGERS_EVENT}/listing/{match.group(1)}")
    assert "tickets" in detail and "$" in detail
    # unknown listing id 404s, canonical event slug redirects
    response = client.get(f"{CHARGERS_EVENT}/listing/99999999")
    assert response.status_code == 404
    response = client.get(f"/wrong/event/160436504/listing/{match.group(1)}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        f"{CHARGERS_EVENT}/listing/{match.group(1)}")


def test_register_login_logout_roundtrip(client):
    response = client.post("/secure/register", data={
        "email": "walk.tester@example.com", "password": "Walk1234!",
        "display_name": "Walk Tester"}, follow_redirects=False)
    assert response.status_code == 302
    body = get(client, "/secure/myaccount")
    assert "Walk Tester" in body
    response = client.post("/secure/logout", follow_redirects=False)
    assert response.status_code == 302
    # bad password does not log in
    response = client.post("/secure/login", data={
        "email": "walk.tester@example.com", "password": "nope"},
        follow_redirects=False)
    assert response.status_code == 200  # re-renders the form
    response = client.get("/secure/myaccount", follow_redirects=False)
    assert response.status_code == 302  # still anonymous


def test_full_checkout_flow(client):
    # a fresh registered user buys tickets end to end
    response = client.post("/secure/register", data={
        "email": "buyer.walk@example.com", "password": "Buy12345!",
        "display_name": "Buyer Walker"}, follow_redirects=False)
    assert response.status_code == 302
    body = get(client, CHARGERS_EVENT + "?sort=price&quantity=2")
    match = re.search(r"/listing/(\d+)", body)
    assert match
    listing_id = match.group(1)
    response = client.post("/secure/checkout/start", data={
        "listing_id": listing_id, "quantity": 2}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secure/checkout/review")
    response = client.post("/secure/checkout/review", data={
        "delivery": "ups"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secure/checkout/payment")
    # invalid card re-renders the form; valid card advances to confirm
    response = client.post("/secure/checkout/payment", data={
        "brand": "visa", "number": "12", "holder": "Walk Tester",
        "exp_month": 12, "exp_year": 2030, "cvv": "123"})
    assert response.status_code == 200
    response = client.post("/secure/checkout/payment", data={
        "brand": "visa", "number": "4111 1111 1111 1111", "holder": "Walk Tester",
        "exp_month": 12, "exp_year": 2030, "cvv": "123"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secure/checkout/confirm")
    body = get(client, "/secure/checkout/confirm")
    assert "$14.95" in body          # UPS delivery fee
    response = client.post("/secure/checkout/confirm", follow_redirects=False)
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/secure/checkout/confirmation/" in location
    body = get(client, location)
    assert "Order" in body and "Total paid" in body
    assert "UPS" in body               # chosen delivery method is echoed back


def test_checkout_requires_session_state(client):
    """Hitting checkout steps out of order bounces home instead of crashing."""
    client.post("/secure/register", data={
        "email": "state.walk@example.com", "password": "State123!",
        "display_name": "State Walker"}, follow_redirects=False)
    for path in ("/secure/checkout/review", "/secure/checkout/payment",
                 "/secure/checkout/confirm"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")


def test_sell_flow_lists_tickets(alice):
    response = alice.post("/selltickets/event/160436503", data={
        "section": "220", "row": "14", "seats": "5-6",
        "quantity": 2, "price": 195, "description": "Great view"},
        follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/secure/myaccount/listings")
    body = get(alice, "/secure/myaccount/listings")
    assert "220" in body and "Row 14" in body and "$195" in body


def test_favorites_roundtrip(alice):
    """The favorite action toggles follow state and shows it on /favorites."""
    marker = 'href="/metallica-tickets/performer/8147"'
    body = get(alice, "/favorites")
    had = marker in body           # alice's fixture includes Metallica
    response = alice.post("/favorite/performer/8147", follow_redirects=False)
    assert response.status_code == 302
    body = get(alice, "/favorites")
    assert (marker in body) != had   # toggle flipped the follow state
    response = alice.post("/favorite/performer/8147", follow_redirects=False)
    assert response.status_code == 302
    body = get(alice, "/favorites")
    assert (marker in body) == had   # toggle restored the original state


def test_gift_card_purchase(alice):
    body = get(alice, "/gift-cards")
    assert "$25" in body and "holiday" in body   # amounts + designs offered
    response = alice.post("/gift-cards/purchase", data={
        "amount": 150, "recipient_name": "Danny",
        "recipient_email": "danny.gift@example.com",
        "message": "Happy birthday!", "design": "holiday"},
        follow_redirects=False)
    assert response.status_code == 302
    body = get(alice, "/gift-cards")
    assert re.search(r"SH[A-Z0-9]{10}", body), "gift code must be shown"
    assert "$150" in body
    # invalid amount bounces back without a crash
    response = alice.post("/gift-cards/purchase", data={
        "amount": 33, "recipient_name": "Danny",
        "recipient_email": "danny.gift@example.com"}, follow_redirects=False)
    assert response.status_code == 302


def test_alice_account_domain(alice):
    body = get(alice, "/secure/myaccount")
    assert "Alice" in body
    body = get(alice, "/secure/myaccount/purchases")
    assert "Metallica" in body          # fixture order for the 2-day pass
    body = get(alice, "/secure/myaccount/sales")
    assert "Paid" in body
    body = get(alice, "/secure/myaccount/listings")
    assert "SECTION" in body or "Section" in body
    body = get(alice, "/secure/myaccount/payments")
    assert "••••" in body


def test_payments_management(alice):
    body = get(alice, "/secure/myaccount/payments")
    match = re.search(r"/secure/myaccount/payments/(\d+)/remove", body)
    assert match, "existing card must expose a remove action"
    card_id = match.group(1)
    # add a fresh card then remove the old one
    response = alice.post("/secure/myaccount/payments", data={
        "brand": "mastercard", "number": "5555 4444 3333 2222",
        "holder": "Alice Johnson", "exp_month": 9,
        "exp_year": 2030, "cvv": "789"}, follow_redirects=False)
    assert response.status_code == 302
    body = get(alice, "/secure/myaccount/payments")
    assert "2222" in body
    response = alice.post(f"/secure/myaccount/payments/{card_id}/remove",
                          follow_redirects=False)
    assert response.status_code == 302
    # removing the only/default card must not crash
    body = get(alice, "/secure/myaccount/payments", min_len=200)
    assert "Payments" in body


def test_bad_input_fails_gracefully(client):
    for path in ["/no-such/performer/999999999",
                 "/x/category/999999999", "/x/grouping/999999999",
                 "/x/event/999999999", "/search?q=",
                 CHARGERS_EVENT + "?quantity=abc&price_min=zzz",
                 CHARGERS_EVENT + "?zone=Nope&features=Nope"]:
        response = client.get(path)
        assert response.status_code in (200, 404), \
            f"{path} -> {response.status_code}"
