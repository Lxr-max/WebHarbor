"""Flow tests with CSRF enabled: account creation, watchlist toggles and
price-alert lifecycle, exactly the way a browser drives them."""
import re

import app as nyse_app
from conftest import with_csrf

from app import PriceAlert, Quote, WatchItem, db


class TestSignupLogin:
    def test_signup_creates_and_logs_in(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Test Investor", "email": "investor.t@test.com",
            "password": "TestPass456!"})
        r = client.post("/signup", data=data, follow_redirects=True)
        assert r.status_code == 200
        assert b"investor.t@test.com" not in r.data  # never echo the email
        assert b"Log Out" in r.data

    def test_signup_rejects_short_password(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Short Pw", "email": "short.pw@test.com",
            "password": "short"})
        r = client.post("/signup", data=data)
        assert r.status_code == 200
        assert b"at least 8 characters" in r.data

    def test_signup_rejects_duplicate_email(self, client):
        data = with_csrf(client, "/signup", {
            "name": "Alice Again", "email": "alice.j@test.com",
            "password": "TestPass456!"})
        r = client.post("/signup", data=data)
        assert b"already exists" in r.data

    def test_login_rejects_bad_password(self, client):
        data = with_csrf(client, "/login", {
            "email": "alice.j@test.com", "password": "wrong"})
        r = client.post("/login", data=data)
        assert r.status_code == 200
        assert b"Invalid email or password" in r.data

    def test_login_redirects_to_next(self, client):
        data = with_csrf(client, "/login?next=/watchlist", {
            "email": "alice.j@test.com", "password": "TestPass123!",
            "next": "/watchlist"})
        r = client.post("/login", data=data)
        assert r.status_code in (302, 303)
        assert r.headers["Location"].endswith("/watchlist")

    def test_unsigned_login_post_rejected(self, client):
        r = client.post("/login", data={"email": "alice.j@test.com",
                                        "password": "TestPass123!"})
        assert r.status_code == 400  # CSRF fails closed


class TestWatchlist:
    def test_watchlist_requires_login(self, client):
        r = client.get("/watchlist")
        assert r.status_code in (302, 303)

    def test_alice_watchlist_seeded(self, alice_client):
        r = alice_client.get("/watchlist")
        assert r.status_code == 200
        html = r.data.decode()
        for sym in ("KO", "DIS", "NKE"):
            assert sym in html

    def test_toggle_add_and_remove(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:IBM", {
            "symbol": "IBM", "back": "/watchlist"})
        r = alice_client.post("/watchlist/toggle", data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        assert b"IBM" in r.data
        # Toggle again removes it.
        r2 = alice_client.post("/watchlist/toggle", data=data,
                               follow_redirects=True)
        body = r2.data.decode()
        rows = re.findall(r"<td><a href=\"/quote/[^\"]+\">([A-Z.]+)</a>",
                          body)
        assert "IBM" not in rows

    def test_toggle_fails_closed_on_unknown_symbol(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:KO", {
            "symbol": "NOPE99", "back": "/watchlist"})
        r = alice_client.post("/watchlist/toggle", data=data)
        assert r.status_code == 400

    def test_unsigned_toggle_rejected(self, client):
        r = client.post("/watchlist/toggle", data={"symbol": "KO"})
        assert r.status_code in (302, 303, 400)


class TestPriceAlerts:
    def test_alerts_page_requires_login(self, client):
        r = client.get("/alerts")
        assert r.status_code in (302, 303)

    def test_bob_alerts_seeded(self, bob_client):
        r = bob_client.get("/alerts")
        html = r.data.decode()
        assert "AAPL" in html and "TSLA" in html

    def test_alert_lifecycle(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:IBM", {
            "symbol": "IBM", "direction": "above", "threshold": "100.50",
            "note": "Momentum level"})
        r = alice_client.post("/alerts/create", data=data,
                              follow_redirects=True)
        assert r.status_code == 200
        html = r.data.decode()
        assert "100.50" in html and "Momentum level" in html
        with nyse_app.app.app_context():
            row = PriceAlert.query.filter_by(symbol="IBM",
                                             threshold=100.50).first()
        assert row is not None
        # Delete it again.
        data = with_csrf(alice_client, "/alerts", {"id": str(row.id)})
        r2 = alice_client.post("/alerts/delete", data=data,
                               follow_redirects=True)
        assert r2.status_code == 200
        with nyse_app.app.app_context():
            assert PriceAlert.query.filter_by(id=row.id).first() is None

    def test_alert_rejects_bad_direction(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:KO", {
            "symbol": "KO", "direction": "sideways", "threshold": "100"})
        r = alice_client.post("/alerts/create", data=data)
        assert r.status_code == 400

    def test_alert_rejects_bad_threshold(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:KO", {
            "symbol": "KO", "direction": "above", "threshold": "banana"})
        r = alice_client.post("/alerts/create", data=data)
        assert r.status_code == 400

    def test_alert_rejects_unknown_symbol(self, alice_client):
        data = with_csrf(alice_client, "/quote/XNYS:KO", {
            "symbol": "NOPE99", "direction": "above", "threshold": "5"})
        r = alice_client.post("/alerts/create", data=data)
        assert r.status_code == 400

    def test_alert_state_deterministic(self, bob_client):
        # Bob's seeded AAPL alert (below 300) against the captured price.
        from app import alert_state
        with nyse_app.app.app_context():
            alert = PriceAlert.query.filter_by(symbol="AAPL").first()
            quote = db.session.get(Quote, "AAPL")
            expected = ("triggered" if quote.last <= alert.threshold
                        else "pending")
            assert alert_state(alert) == expected
        r = bob_client.get("/alerts")
        html = r.data.decode()
        assert ("Triggered" if expected == "triggered" else "Pending") in html

    def test_alert_delete_ignores_foreign_ids(self, alice_client, bob_client):
        with nyse_app.app.app_context():
            bob_alert = PriceAlert.query.filter_by(symbol="AAPL").first()
        data = with_csrf(alice_client, "/alerts", {"id": str(bob_alert.id)})
        alice_client.post("/alerts/delete", data=data)
        with nyse_app.app.app_context():
            assert (PriceAlert.query.filter_by(id=bob_alert.id).first()
                    is not None)


class TestSeedDeterminism:
    def test_watch_counts(self, alice_client, bob_client, carol_client,
                          dana_client):
        for cli, expected in ((alice_client, 3), (bob_client, 2),
                              (carol_client, 1), (dana_client, 3)):
            html = cli.get("/watchlist").data.decode()
            rows = re.findall(r"<td><a href=\"/quote/[^\"]+\">([A-Z.]+)</a>",
                              html)
            assert len(rows) == expected, rows
