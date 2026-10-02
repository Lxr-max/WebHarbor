"""Flow tests — CSRF stays enabled for every form submission."""
from __future__ import annotations

import re


def _csrf(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "csrf token missing"
    return m.group(1)


# ------------------------------------------------------------------ public --

def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Simplicity Plan" in r.data


def test_plans_line_selector(client):
    r = client.get("/plans/?lines=4")
    assert r.status_code == 200
    assert b"$120" in r.data
    assert b"After AutoPay and $15/mo switch discount" in r.data


def test_prepaid_plans(client):
    r = client.get("/prepaid/")
    assert r.status_code == 200
    for anchor in (b"Talk &amp; Text", b"15 GB", b"Unlimited Plus", b"$60.00",
                   b"3-year price lock guarantee"):
        assert anchor in r.data


def test_gridwall_filter_sort(client):
    r = client.get("/smartphones/?brand=Samsung&sort=price-asc")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Samsung Galaxy A17 5G" in body
    assert "Apple iPhone 18 Pro" not in body


def test_device_pdp(client):
    r = client.get("/smartphones/apple-iphone-18-pro/")
    assert r.status_code == 200
    body = r.data.decode()
    for anchor in ("Full retail price: $1,199.99", "$49.99/mo", "Burgundy",
                   "Typical use: Up to 24 hours", "$210.00"):
        assert anchor in body


def test_purchase_flow(client):
    """Configure -> cart -> checkout -> confirmation, with CSRF on every post."""
    html = client.get("/smartphones/motorola-moto-g-2026/configure").get_data(as_text=True)
    r = client.post("/smartphones/motorola-moto-g-2026/configure",
                    data={"csrf_token": _csrf(html), "storage": "Single capacity",
                          "term": "36", "protection": "Verizon Mobile Protect",
                          "plan": "1"}, follow_redirects=True)
    assert r.status_code == 200
    assert b"Your cart" in r.data
    assert b"Verizon Mobile Protect" in r.data

    html = client.get("/cart/").get_data(as_text=True)
    assert "$54.77" in html
    html = client.get("/checkout/").get_data(as_text=True)
    r = client.post("/checkout/",
                    data={"csrf_token": _csrf(html), "name": "Jordan Pratt",
                          "email": "jordan.pratt@example.com",
                          "street": "88 Pine Street", "city": "Seattle",
                          "state": "WA", "zip": "98101"},
                    follow_redirects=True)
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert re.search(r"Order VZW\d+", body)
    assert "$54.77/mo" in body


def test_trade_in_estimate(client):
    html = client.get("/trade-in/estimate/").get_data(as_text=True)
    r = client.post("/trade-in/estimate/",
                    data={"csrf_token": _csrf(html),
                          "device": "Google Pixel 11", "condition": "Good"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"$300.00" in r.data


def test_store_locator_and_appointment(client):
    r = client.get("/stores/washington/seattle/")
    assert r.status_code == 200
    assert "Seattle Northgate" in r.get_data(as_text=True)
    r = client.get("/store/r00000151174/")
    assert b"10:00 AM 06:00 PM" in r.data
    html = client.get("/store/r00000151174/appointment/").get_data(as_text=True)
    r = client.post("/store/r00000151174/appointment/",
                    data={"csrf_token": _csrf(html), "name": "Sam Rivera",
                          "email": "sam.rivera@example.com", "phone": "206-555-0139",
                          "topic": "Device trade-in", "date": "2026-10-06",
                          "time": "02:00 PM"}, follow_redirects=True)
    assert r.status_code == 200
    assert re.search(r"Confirmation APT\d+", r.get_data(as_text=True))


def test_support_pages(client):
    r = client.get("/support/return-policy/")
    assert r.status_code == 200
    assert b"$50" in r.data
    r = client.get("/support/contact-us/")
    assert b"800-225-5499" in r.data


def test_troubleshoot_wizard(client):
    html = client.get("/support/troubleshoot/").get_data(as_text=True)
    r = client.post("/support/troubleshoot/",
                    data={"csrf_token": _csrf(html), "family": "Google",
                          "issue": "No service or cannot connect to the network"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert b"Check the coverage map for your address." in r.data


# ----------------------------------------------------------------- account --

def test_login_required_redirect(client):
    r = client.get("/account/")
    assert r.status_code == 302


def test_bad_login_rejected(client):
    html = client.get("/account/login").get_data(as_text=True)
    r = client.post("/account/login",
                    data={"csrf_token": _csrf(html),
                          "email": "alice.j@test.com", "password": "wrong"},
                    follow_redirects=True)
    assert b"Invalid email or password." in r.data


def test_bill_detail_and_pay(alice):
    r = alice.get("/account/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "8472-0913" in body
    m = re.search(r'href="(/account/bills/(\d+)/)"', body)
    r = alice.get(m.group(1))
    page = r.get_data(as_text=True)
    assert "$160.62" in page
    assert "Verizon Mobile Protect — Alice" in page

    html = alice.get("/account/pay/").get_data(as_text=True)
    r = alice.post("/account/pay/",
                   data={"csrf_token": _csrf(html), "amount": "160.62",
                         "method": "Card ending 4242"}, follow_redirects=True)
    assert r.status_code == 200
    assert re.search(r"Confirmation PMT\d+", r.get_data(as_text=True))


def test_bob_unpaid_bill(bob):
    r = bob.get("/account/pay/")
    assert r.status_code == 200
    assert b"$118.17" in r.data


def test_autopay_enrollment(carol):
    assert b"Auto Pay: Off" in carol.get("/account/").data
    html = carol.get("/account/autopay/").get_data(as_text=True)
    r = carol.post("/account/autopay/",
                   data={"csrf_token": _csrf(html), "autopay": "on",
                         "paper_free": "on"}, follow_redirects=True)
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Auto Pay and billing preferences updated." in body
    assert "Auto Pay: Enrolled" in body


def test_usage(alice):
    r = alice.get("/account/usage/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "31.4" in body and "9.6" in body
    assert "10 GB mobile hotspot allowance" in body


def test_change_plan(dana):
    r = dana.get("/account/")
    assert "Unlimited Plus ($70.00/mo)" in r.get_data(as_text=True)
    m = re.search(r'href="(/account/lines/(\d+)/change-plan)"',
                  r.get_data(as_text=True))
    r = dana.get(m.group(1))
    assert r.status_code == 200
    html = dana.get(m.group(1)).get_data(as_text=True)
    r = dana.post(m.group(1), data={"csrf_token": _csrf(html), "plan": "4"},
                  follow_redirects=True)
    assert r.status_code == 200
    assert "Plan for Dana changed to Unlimited." in r.get_data(as_text=True)


def test_add_line(alice):
    html = alice.get("/account/add-line/").get_data(as_text=True)
    r = alice.post("/account/add-line/",
                   data={"csrf_token": _csrf(html), "nickname": "Mom",
                         "device": "18", "plan": "1"}, follow_redirects=True)
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Lines on this account (3)" in body


def test_order_status(bob):
    r = bob.get("/account/orders/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "In transit" in body
    m = re.search(r'href="(/account/orders/(VZW\d+)/)"', body)
    r = bob.get(m.group(1))
    page = r.get_data(as_text=True)
    assert "Arriving by Thu, Oct 1" in page
    assert "$36.94/mo" in page


def test_logout(alice):
    r = alice.get("/account/logout", follow_redirects=False)
    assert r.status_code == 302
    r = alice.get("/account/")
    assert r.status_code == 302


def test_rendered_images_resolve(client):
    """Every <img> URL rendered on key pages must serve 200 (>100 bytes)."""
    pages = ["/", "/smartphones/", "/smartphones/apple-iphone-18-pro/",
             "/smartphones/motorola-moto-g-2026/configure",
             "/stores/washington/seattle/", "/store/r00000151174/"]
    import re as _re
    import pathlib
    seen = set()
    for path in pages:
        html = client.get(path).get_data(as_text=True)
        for url in _re.findall(r'src="(/static/images/[^"]+)"', html):
            if url in seen:
                continue
            seen.add(url)
            local = (pathlib.Path(__file__).resolve().parents[1] / "static"
                     / url.removeprefix("/static/"))
            assert local.is_file(), f"rendered image missing on disk: {url}"
            assert local.stat().st_size > 100, f"rendered image too small: {url}"
    assert len(seen) >= 8, f"expected several rendered images, got {len(seen)}"


def test_a17_pdp_lists_upstream_storage_and_ship_window(client):
    """r1 N-1 fix: the cheapest Samsung (Galaxy A17 5G) PDP must render the
    real upstream single-capacity storage line and the real upstream
    fulfillment line (captured 2026-09-29, re-verified live on the fix date):
    "Storage: 128 GB" and "Free shipping by Thursday with new line"."""
    html = client.get("/smartphones/samsung-galaxy-a17-5g/").get_data(as_text=True)
    assert "Storage options: 128 GB" in html
    assert "Free shipping by Thursday with new line" in html


def test_a17_configure_offers_the_128_gb_capacity(client):
    html = client.get("/smartphones/samsung-galaxy-a17-5g/configure").get_data(as_text=True)
    assert 'name="storage"' in html
    assert 'value="128 GB"' in html


def test_cart_renders_per_item_monthly_lines(client, csrf):
    """r3 fix (T18): the cart must render each item's own monthly line
    (device payment + protection + plan service) next to the combined
    monthly total, mirroring the T18 two-phone configuration."""
    def add(slug, fields):
        html = client.get(f"/smartphones/{slug}/configure").get_data(as_text=True)
        payload = {"csrf_token": csrf(html), "plan": "1"}  # checked Simplicity radio
        payload.update(fields)
        client.post(f"/smartphones/{slug}/configure", data=payload)

    add("apple-iphone-18-pro",
        {"color": "Glacier", "storage": "2 TB", "term": "24"})
    add("samsung-galaxy-s26-ultra",
        {"color": "Cobalt Violet", "storage": "512 GB", "term": "24"})
    html = client.get("/cart/").get_data(as_text=True)
    assert "Monthly line" in html, "cart must render a per-item monthly column"
    assert "$79.99/mo" in html, "iPhone 18 Pro item monthly (24 mos + Simplicity)"
    assert "$84.16/mo" in html, "S26 Ultra item monthly (24 mos + Simplicity)"
    assert "Monthly total: $164.15" in html, "combined monthly total"
    assert html.count("/mo</td>") == 2, "exactly one monthly line per item"
