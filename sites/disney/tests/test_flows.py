"""Flow tests: auth, favorites, bag/checkout, ticket booking, search and
CSRF enforcement — all with CSRF protection enabled and real tokens."""
import re

from conftest import with_csrf


class TestAuth:
    def test_login_success(self, client):
        data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                            "password": "TestPass123!"})
        r = client.post("/login", data=data)
        assert r.status_code in (302, 303)

    def test_login_failure(self, client):
        data = with_csrf(client, "/login", {"email": "alice.j@test.com",
                                           "password": "WrongPass999!"})
        r = client.post("/login", data=data)
        assert r.status_code == 200
        assert b"Invalid email or password" in r.data

    def test_signup_and_favorites_persist(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Flow Tester", "email": "flow.tester@test.com",
            "password": "LongPass123!"})
        r = client.post("/signup", data=data)
        assert r.status_code in (302, 303)
        data = with_csrf(client, "/movies/moana-2", {
            "type": "movie", "key": "moana-2", "back": "/movies/moana-2"})
        r = client.post("/favorites/toggle", data=data)
        assert r.status_code in (302, 303)
        r = client.get("/favorites")
        assert b"Moana 2" in r.data

    def test_duplicate_signup_rejected(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Dup", "email": "alice.j@test.com",
            "password": "LongPass123!"})
        r = client.post("/signup", data=data)
        assert b"already exists" in r.data

    def test_favorites_require_login(self, client):
        r = client.get("/favorites")
        assert r.status_code in (302, 303)


class TestFavorites:
    def test_alice_fixture_state(self, alice_client):
        r = alice_client.get("/favorites")
        html = r.data.decode()
        assert "Moana 2" in html and "Toy Story 5" in html
        assert "Seven Dwarfs Mine Train" in html

    def test_bob_fixture_state(self, bob_client):
        r = bob_client.get("/favorites")
        html = r.data.decode()
        assert "Gravity Falls" in html and "DuckTales" in html
        assert "Fantasmic" in html

    def test_carol_product_favorites(self, carol_client):
        r = carol_client.get("/favorites")
        assert b"<h2>Shop</h2>" in r.data  # shop section renders
        assert b"Buzz Lightyear Flying RC Hi-Tech Edition" in r.data

    def test_dana_fixture_state(self, dana_client):
        r = dana_client.get("/favorites")
        html = r.data.decode()
        assert "Hoppers" in html
        assert "Living with the Land" in html

    def test_toggle_removes(self, alice_client):
        data = with_csrf(alice_client, "/movies/moana-2", {
            "type": "movie", "key": "moana-2", "back": "/movies/moana-2"})
        alice_client.post("/favorites/toggle", data=data)
        r = alice_client.get("/favorites")
        html = r.data.decode()
        assert "Moana 2" not in html.split("Shows")[0]

    def test_park_entity_favorite(self, dana_client):
        """The favorites form on an attraction page must post the full
        park/slug key the /favorites page resolves — a bare slug would
        count without ever rendering (the r1 review defect)."""
        page = dana_client.get(
            "/parks/attractions/epcot/soarin-around-world").data.decode()
        m = re.search(
            r'name="type" value="([^"]+)".*?name="key" value="([^"]+)"',
            page, re.S)
        assert m, "no favorites form rendered on the attraction page"
        assert m.group(1) == "attraction"
        assert m.group(2) == "epcot/soarin-around-world", m.group(2)
        data = with_csrf(
            dana_client,
            "/parks/attractions/epcot/soarin-around-world",
            {"type": m.group(1), "key": m.group(2),
             "back": "/parks/attractions/epcot/soarin-around-world"})
        r = dana_client.post("/favorites/toggle", data=data)
        assert r.status_code in (302, 303)
        r = dana_client.get("/favorites")
        html = r.data.decode()
        assert "Soarin" in html
        # the printed count and the rendered cards must agree
        assert "4 favorites" in html
        assert "Hoppers" in html and "Living with the Land" in html

    def test_favorites_unknown_key_rejected(self, alice_client):
        """Fail closed: a favorite that resolves to no catalog row must
        be rejected, or it would count without rendering."""
        data = with_csrf(
            alice_client, "/movies/moana-2",
            {"type": "attraction", "key": "no-such-park/no-such-slug"})
        r = alice_client.post("/favorites/toggle", data=data)
        assert r.status_code == 400


class TestBagAndCheckout:
    def test_bag_add_update_checkout(self, client):
        # add 2 of the Blaze doll set
        data = with_csrf(client, "/shop/products/416120537041",
                         {"pid": "416120537041", "qty": "2"})
        r = client.post("/bag/add", data=data)
        assert r.status_code in (302, 303)
        r = client.get("/bag")
        assert b"Blaze Doll Set" in r.data
        m = re.search(r"Total: \$([\d.]+)", r.data.decode())
        assert m and float(m.group(1)) == 129.98
        # change quantity to 1
        row = re.search(r'name="row_id" value="(\d+)"',
                        r.data.decode()).group(1)
        data = with_csrf(client, "/bag", {"row_id": row, "qty": "1"})
        client.post("/bag/update", data=data)
        r = client.get("/bag")
        m = re.search(r"Total: \$([\d.]+)", r.data.decode())
        assert m and float(m.group(1)) == 64.99
        # checkout as guest
        data = with_csrf(client, "/checkout", {
            "name": "Flow Buyer", "email": "flow.buyer@example.com",
            "address": "1 Main Street"})
        r = client.post("/checkout", data=data)
        assert r.status_code in (302, 303)
        confirm = re.search(r"/order/([A-Z0-9]+)",
                            r.headers.get("Location", ""))
        assert confirm
        r = client.get(f"/order/{confirm.group(1)}")
        assert b"confirmation code" in r.data
        assert b"64.99" in r.data
        # bag is empty after checkout
        r = client.get("/bag")
        assert b"Your bag is empty" in r.data

    def test_checkout_validation(self, client):
        data = with_csrf(client, "/shop/products/416120537041",
                         {"pid": "416120537041", "qty": "1"})
        client.post("/bag/add", data=data)
        data = with_csrf(client, "/checkout",
                         {"name": "", "email": "not-an-email",
                          "address": ""})
        r = client.post("/checkout", data=data)
        assert r.status_code == 200
        assert b"Enter your full name" in r.data

    def test_bag_remove_with_zero_qty(self, client):
        data = with_csrf(client, "/shop/products/416120537041",
                         {"pid": "416120537041", "qty": "1"})
        client.post("/bag/add", data=data)
        r = client.get("/bag")
        row = re.search(r'name="row_id" value="(\d+)"',
                        r.data.decode()).group(1)
        data = with_csrf(client, "/bag", {"row_id": row, "qty": "0"})
        client.post("/bag/update", data=data)
        r = client.get("/bag")
        assert b"Your bag is empty" in r.data


class TestTicketBooking:
    def test_book_tickets_flow(self, client):
        r = client.get("/live-shows/disney-on-ice/120960")
        assert r.status_code == 200
        data = with_csrf(client, "/live-shows/disney-on-ice/120960/book", {
            "day": "Oct 24, 2026", "time": "11:00 am", "qty": "3",
            "name": "Flow Skater", "email": "flow.skater@example.com"})
        r = client.post("/live-shows/disney-on-ice/120960/book", data=data)
        assert r.status_code in (302, 303)
        code = re.search(r"/tickets/([A-Z0-9]+)",
                         r.headers.get("Location", ""))
        assert code
        r = client.get(f"/tickets/{code.group(1)}")
        html = r.data.decode()
        assert "Jump In!" in html and "Kent, WA" in html
        assert "Oct 24, 2026" in html and "11:00 am" in html
        assert "105.00" in html

    def test_booking_validation(self, client):
        data = with_csrf(client, "/live-shows/disney-on-ice/120960/book", {
            "day": "", "time": "", "qty": "0",
            "name": "", "email": "x"})
        r = client.post("/live-shows/disney-on-ice/120960/book", data=data)
        assert r.status_code == 200
        assert b"Choose a performance date" in r.data

    def test_booking_rejects_invalid_performance(self, client):
        data = with_csrf(client, "/live-shows/disney-on-ice/120960/book", {
            "day": "Dec 25, 2026", "time": "9:00 am", "qty": "1",
            "name": "X", "email": "x@example.com"})
        r = client.post("/live-shows/disney-on-ice/120960/book", data=data)
        assert b"Choose a performance date" in r.data

    def test_bob_fixture_ticket_order(self, bob_client):
        from app import TicketOrder
        order = TicketOrder.query.filter_by(email="bob.c@test.com").first()
        assert order and order.qty == 2
        r = bob_client.get(f"/tickets/{order.confirmation}")
        assert r.status_code == 200
        assert b"TK2M8N4P6R" in r.data


class TestSearch:
    def test_search_sections(self, client):
        r = client.get("/search?q=frozen")
        html = r.data.decode()
        assert "Movies (1)" in html
        assert "Parks &amp; Entertainment (3)" in html
        assert "Shop (2)" in html

    def test_search_lists_full_results(self, client):
        """Section counts are the true match counts: every match is
        listed, so a reported count always equals what the page shows
        (the r1 review flagged the old 12-item cap)."""
        r = client.get("/search?q=plush")
        html = r.data.decode()
        assert "Shop (25)" in html
        assert html.count('href="/shop/products/') == 25
        r = client.get("/search?q=mickey")
        html = r.data.decode()
        assert "Parks &amp; Entertainment (13)" in html
        assert "Shows (2)" in html

    def test_search_links_resolve(self, client):
        r = client.get("/search?q=moana")
        for href in re.findall(r'href="(/[a-z0-9/-]+)"', r.data.decode()):
            assert client.get(href).status_code == 200, href


class TestCSRF:
    """CSRF protection is enabled globally; unsigned state-changing
    requests must be rejected."""

    def test_login_requires_token(self, client):
        r = client.post("/login", data={"email": "alice.j@test.com",
                                        "password": "TestPass123!"})
        assert r.status_code == 400

    def test_bag_add_requires_token(self, client):
        r = client.post("/bag/add", data={"pid": "416120537041", "qty": "1"})
        assert r.status_code == 400

    def test_checkout_requires_token(self, client):
        r = client.post("/checkout", data={"name": "x", "email": "e@e.com",
                                           "address": "a"})
        assert r.status_code == 400

    def test_booking_requires_token(self, client):
        r = client.post("/live-shows/disney-on-ice/120960/book",
                        data={"day": "d", "time": "t", "qty": "1",
                              "name": "n", "email": "e@e.com"})
        assert r.status_code == 400

    def test_signup_requires_token(self, client):
        r = client.post("/signup", data={"name": "x", "email": "x@x.com",
                                         "password": "LongPass123!"})
        assert r.status_code == 400

    def test_favorites_toggle_requires_token(self, alice_client):
        r = alice_client.post("/favorites/toggle",
                              data={"type": "movie", "key": "moana-2"})
        assert r.status_code == 400
