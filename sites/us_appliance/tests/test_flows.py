"""Flow tests: benchmark-user journeys through cart, checkout, orders, tracking."""
import json
import re


def _extract_order_number(html):
    m = re.search(r"order number is <strong>#(\d+)", html)
    return m.group(1) if m else None


def test_register_login_logout(client):
    resp = client.post("/login.php?action=create_account",
                       data={"email": "new.user@example.com",
                             "password": "Passw0rd123", "name": "New User"},
                       follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "My Account" in html
    client.get("/logout")
    resp = client.post("/login.php",
                       data={"email": "new.user@example.com",
                             "password": "Passw0rd123"},
                       follow_redirects=True)
    assert b"My Account" in resp.get_data()
    # wrong password
    client.get("/logout")
    resp = client.post("/login.php", data={"email": "new.user@example.com",
                                           "password": "nope"})
    assert resp.status_code == 401


def test_guest_checkout_full_chain(client):
    client.post("/cart.php?action=add", data={"product_id": 21476, "qty": 2})
    client.post("/cart.php?action=add", data={"product_id": 26611, "qty": 1})
    cart = client.get("/cart.php").get_data(as_text=True)
    assert "$2,795.00" in cart            # 2 x 823 + 1149
    assert "FREE standard delivery" in cart

    resp = client.post("/checkout", data={
        "name": "Guest Buyer", "address": "1 Main St", "city": "Troy",
        "state": "MI", "zip": "48083", "email": "guest@example.com",
        "phone": "248-555-0100", "card_number": "4111111111111111",
        "card_expiry": "12/28", "card_cvv": "123",
        "shipping_method": "standard", "financing": ""}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    number = _extract_order_number(html)
    assert number, html[:500]
    assert "Thank You! Your order has been placed." in html
    # subtotal + free shipping + 6% MI tax
    assert "$2,962.70" in html

    # cart is empty again
    cart = client.get("/cart.php").get_data(as_text=True)
    assert "Your cart is empty" in cart

    # tracking lookup with the new number
    resp = client.post("/ordertracking.html",
                       data={"order_number": number,
                             "email": "guest@example.com"})
    html = resp.get_data(as_text=True)
    assert f"Order #{number}" in html
    assert "Processing" in html


def test_in_home_delivery_checkout(client):
    client.post("/cart.php?action=add", data={"product_id": 16435, "qty": 1})
    resp = client.post("/checkout", data={
        "name": "Ohio Buyer", "address": "9 Elm St", "city": "Columbus",
        "state": "OH", "zip": "43215", "email": "ohio@example.com",
        "phone": "", "card_number": "4111111111111111",
        "card_expiry": "01/29", "card_cvv": "999",
        "shipping_method": "in_home",
        "financing": "15 Months Special Financing"}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "$878.00" in html            # 679 + 199 in-home shipping, no OH tax


def test_checkout_validation(client):
    client.post("/cart.php?action=add", data={"product_id": 16435, "qty": 1})
    resp = client.post("/checkout", data={
        "name": "", "address": "", "city": "", "state": "MICH",
        "zip": "12", "email": "bad", "card_number": "123",
        "card_expiry": "13", "card_cvv": "1",
        "shipping_method": "standard", "financing": ""})
    html = resp.get_data(as_text=True)
    assert "Name is required" in html
    assert "Use a 2-letter state code" in html
    assert "Enter a valid email" in html


def test_alice_orders_and_detail(alice):
    html = alice.get("/account.php").get_data(as_text=True)
    assert "Alice Johnson" in html
    assert "Order #10001" in html and "Order #10002" in html
    assert "Delivered" in html and "Shipped" in html
    # order detail page
    resp = alice.get("/account.php/orders/1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "R+L Carriers" in html
    assert "RL774912" in html
    assert "Order Placed" in html
    assert "Delivered" in html
    # in-home delivery cost on the seeded order
    assert "$199.00" in html


def test_order_email_isolation(alice, bob):
    # bob cannot open alice's order detail
    resp = bob.get("/account.php/orders/1")
    assert resp.status_code == 404


def test_tracking_lookup_requires_email_match(client):
    resp = client.post("/ordertracking.html",
                       data={"order_number": "10003",
                             "email": "alice.j@test.com"})
    html = resp.get_data(as_text=True)
    assert "do not match our records" in html
    resp = client.post("/ordertracking.html",
                       data={"order_number": "10003",
                             "email": "bob.c@test.com"})
    html = resp.get_data(as_text=True)
    assert "Order #10003" in html
    assert "In Transit" in html
    assert "Valley Companies" in html
    assert "VC559201" in html


def test_cart_login_merge(client, alice):
    client.post("/cart.php?action=add", data={"product_id": 21476, "qty": 1})
    alice.post("/login.php", data={"email": "alice.j@test.com",
                                   "password": "TestPass123!"},
               follow_redirects=True)
    html = alice.get("/cart.php").get_data(as_text=True)
    assert "JGBS66REKSS" in html


def test_price_match_submission(client):
    resp = client.post("/price-match-request.html", data={
        "name": "Carol D", "email": "carol@example.com", "phone": "",
        "product": "GE JGBS66REKSS 30\" Gas Range",
        "competitor": "Big Box Store", "price": "799",
        "url": "https://example.com/x"}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Request Received" in html
    assert "$799.00" in html


def test_newsletter_signup(client):
    resp = client.post("/newsletter", data={"nl_email": "deals@example.com"},
                       follow_redirects=True)
    assert b"signed up for deals and offers" in resp.get_data()


def test_seed_idempotence(client):
    # calling the seeded path again must not change any row counts
    with client.application.app_context():
        from app import (seed_benchmark_users, seed_database, FaqItem,
                         MerchantReview, Order, Product, Rebate, User)
        before = (Product.query.count(), User.query.count(),
                  Order.query.count(), MerchantReview.query.count(),
                  Rebate.query.count(), FaqItem.query.count())
        seed_database()
        seed_benchmark_users()
        after = (Product.query.count(), User.query.count(),
                 Order.query.count(), MerchantReview.query.count(),
                 Rebate.query.count(), FaqItem.query.count())
        assert before == after
        assert before[0] >= 12000
