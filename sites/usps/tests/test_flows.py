"""Flow tests: calculator, tracking, wizard flows, store, claims, search.

CSRF protection is ENABLED for this whole suite (reviewer F-1): every
POST fetches the rendered form page first and submits the real token,
exactly like a browser would.
"""
import json
import re

from conftest import with_csrf


def _rows(body):
    return re.findall(r'class="totals">\$([0-9.]+)</td>', body)


def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Quick Tools" in body
    assert "Track a Package" in body
    assert "Latest News" in body
    assert "/static/images/chrome/pme-supplies-26.jpg" in body
    # F-9: the shopping cart is reachable from the site header
    assert 'href="/store/cart"' in body


def _assert_post_forms_tokenized(body, page):
    forms = re.findall(r'<form[^>]*method="post".*?</form>', body, re.S)
    assert forms, f"no POST form on {page}"
    for form in forms:
        assert 'name="csrf_token"' in form, \
            f"POST form on {page} lacks csrf_token input"
    return len(forms)


def test_csrf_tokens_in_public_post_forms(client):
    """F-1 regression: every public POST form embeds the CSRF token."""
    checked = 0
    for page in ["/login", "/tracking/", "/postcalc/letters",
                 "/postcalc/packages", "/postcalc/international",
                 "/pickup/", "/store/stamps", "/store/stamps-all",
                 "/store/stamps-new-releases",
                 "/store/product/breast-cancer-research-stamps-S_555304",
                 "/manage/change-address/request",
                 "/po-boxes/reserve/boston-ma-02205"]:
        checked += _assert_post_forms_tokenized(
            client.get(page).data.decode(), page)
    assert checked >= 13


def test_csrf_tokens_in_clicknship_forms(alice):
    """F-1 regression: wizard POST forms embed the token."""
    assert _assert_post_forms_tokenized(
        alice.get("/clicknship/create?step=1").data.decode(),
        "/clicknship/create?step=1")
    alice.post("/clicknship/create?step=1", follow_redirects=True,
               data=with_csrf(alice, "/clicknship/create?step=1",
                              {"next_step": "2", "sender_name": "Alice Johnson", "sender_street": "123 Pine St", "sender_city": "Seattle", "sender_state": "WA", "sender_zip": "98101", "recipient_name": "Marcus Johnson", "recipient_street": "500 SW Pine St", "recipient_city": "Portland", "recipient_state": "OR", "recipient_zip": "97204"}))
    assert _assert_post_forms_tokenized(
        alice.get("/clicknship/create?step=2").data.decode(),
        "/clicknship/create?step=2")


def test_csrf_tokens_in_claims_forms(bob):
    """F-1 regression: claims + save-tracking POST forms embed the token."""
    assert _assert_post_forms_tokenized(
        bob.get("/claims/file").data.decode(), "/claims/file")
    assert _assert_post_forms_tokenized(
        bob.get("/claims/status").data.decode(), "/claims/status")
    assert _assert_post_forms_tokenized(
        bob.get("/tracking/9405500000000000000003").data.decode(),
        "tracking result save form")


def test_csrf_tokens_in_hold_mail_form(carol):
    """F-1 regression: hold mail request POST form embeds the token."""
    assert _assert_post_forms_tokenized(
        carol.get("/manage/hold-mail/request").data.decode(),
        "/manage/hold-mail/request")


def test_csrf_rejects_missing_token(client):
    r = client.post("/postcalc/packages", data={"weight": "5", "zone": "4"})
    assert r.status_code == 400  # CSRF protection is armed, not disabled


def test_calculator_letters(client):
    data = with_csrf(client, "/postcalc/letters", {"shape": "stamped",
                                                   "ounces": "3"})
    r = client.post("/postcalc/letters", data=data)
    assert "$1.40" in r.data.decode()
    data = with_csrf(client, "/postcalc/letters", {"shape": "postcards"})
    r = client.post("/postcalc/letters", data=data)
    assert "$0.65" in r.data.decode()
    data = with_csrf(client, "/postcalc/letters", {"shape": "stamped",
                                                   "ounces": "5"})
    r = client.post("/postcalc/letters", data=data)
    assert "large envelope" in r.data.decode().lower()


def test_calculator_packages(client):
    data = with_csrf(client, "/postcalc/packages", {"weight": "5", "zone": "4"})
    r = client.post("/postcalc/packages", data=data)
    rows = _rows(r.data.decode())
    assert "7.34" in rows      # Media Mail
    assert "15.80" in rows     # Ground Advantage
    assert "17.50" in rows     # Priority Mail
    body = r.data.decode()
    assert "$34.00" in body    # Large Flat Rate Box


def test_calculator_packages_accepts_decimal_weights(client):
    """F-2: the weight input must accept 4.2 lb (step used to be 0.5)."""
    body = client.get("/postcalc/packages").data.decode()
    assert 'step="0.1"' in body


def test_calculator_packages_service_order(client):
    """F-13: results are in canonical service order, not price-sorted."""
    data = with_csrf(client, "/postcalc/packages", {"weight": "8", "zone": "4"})
    body = client.post("/postcalc/packages", data=data).data.decode()
    labels = re.findall(r"<tr><td>([^<]+)</td><td class=\"totals\">", body)
    assert labels[:4] == ["Priority Mail Express", "Priority Mail",
                          "USPS Ground Advantage",
                          "Media Mail (books &amp; media only)"]


def test_calculator_international(client):
    data = with_csrf(client, "/postcalc/international",
                     {"country": "Japan", "weight": "4"})
    rows = _rows(client.post("/postcalc/international", data=data).data.decode())
    assert "78.50" in rows     # PMI group 17
    assert "108.45" in rows    # PMEI group 17
    data = with_csrf(client, "/postcalc/international",
                     {"country": "Canada", "weight": "2"})
    rows = _rows(client.post("/postcalc/international", data=data).data.decode())
    assert "29.05" in rows     # FCPIS group 1 (Canada)


def test_tracking_known_and_unknown(client):
    r = client.get("/tracking/9405500000000000000003")
    body = r.data.decode()
    assert "In Transit" in body
    assert "September 30, 2026" in body
    assert "In Transit to Next Facility" in body
    r = client.get("/tracking/9405500000000000000001")
    assert "Delivered" in r.data.decode()
    r = client.get("/tracking/9999999999999999999999")
    assert "unavailable" in r.data.decode()


def test_tracking_glossary(client):
    r = client.get("/tracking/")
    body = r.data.decode()
    assert "Shipping Label Created" in body
    assert "Out for Delivery" in body


def test_clicknship_flow(alice):
    alice.post("/clicknship/create?step=1", follow_redirects=True, data=with_csrf(
        alice, "/clicknship/create?step=1", {
            "next_step": "2", "sender_name": "Alice Johnson",
            "sender_street": "1420 4th Ave", "sender_city": "Seattle",
            "sender_state": "WA", "sender_zip": "98101",
            "recipient_name": "Marcus Johnson",
            "recipient_street": "500 SW Pine St", "recipient_city": "Portland",
            "recipient_state": "OR", "recipient_zip": "97204"}))
    r = alice.post("/clicknship/create?step=2", follow_redirects=True, data=with_csrf(
        alice, "/clicknship/create?step=2", {
            "next_step": "3", "weight_lbs": "4.2", "box_type": "own",
            "zone": "2"}))
    body = r.data.decode()
    assert "Priority Mail" in body
    # F-7: addresses captured at step 1 survive the later steps
    assert "1420 4th Ave" in body
    assert "500 SW Pine St" in body
    # F-2: 4.2 lb is a valid input value on the weight step
    step2 = alice.get("/clicknship/create?step=2").data.decode()
    assert 'step="0.1"' in step2
    assert 'value="4.2"' in step2
    r = alice.post("/clicknship/label", follow_redirects=True, data=with_csrf(
        alice, "/clicknship/create?step=3", {
            "service": "pm", "insurance": "1", "insured_value": "350",
            "signature": "1"}))
    body = r.data.decode()
    tracking = re.findall(r"9\d{20,}", body)
    assert tracking
    assert "$26.15" in body
    # the new shipment tracks immediately
    r = alice.get(f"/tracking/{tracking[0]}")
    assert "Shipping Label Created" in r.data.decode()
    assert "Signature required" in r.data.decode()   # F-8
    # F-7/F-8 DB-level: sender/recipient kept, signature flag set
    from app import Shipment
    from app import app
    with app.app_context():
        s = Shipment.query.filter_by(tracking_number=tracking[0]).first()
        assert s.sender_name == "Alice Johnson"
        assert s.recipient_city == "Portland"
        assert s.signature_required is True


def test_clicknship_requires_login(client):
    r = client.get("/clicknship/create", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_pickup_flow(client):
    payload = {
        "street": "88 State St", "city": "Boston", "state": "MA",
        "zip": "02110", "pickup_date": "2026-09-30",
        "package_count": "2", "weight": "6",
        "services": ["Priority Mail"], "phone": "(617) 555-0188",
        "email": "carol.d@test.com", "instructions": "front desk"}
    r = client.post("/pickup/", data=with_csrf(client, "/pickup/", payload))
    body = r.data.decode()
    assert re.search(r"PKG-[A-Z0-9]+", body)
    assert "September 30, 2026" in body
    # F-11: resubmitting the same request is idempotent, not a 500
    r2 = client.post("/pickup/", data=with_csrf(client, "/pickup/", payload))
    assert r2.status_code == 200
    assert re.search(r"PKG-[A-Z0-9]+", r2.data.decode())
    # missing address errors
    r = client.post("/pickup/", data=with_csrf(
        client, "/pickup/", {"pickup_date": "2026-09-30"}))
    assert "Enter a complete pickup address" in r.data.decode()


def test_locations_search_and_detail(client):
    r = client.get("/locations/", query_string={"q": "90210"})
    assert "Beverly Hills" in r.data.decode()
    r = client.get("/locations/beverly-hills-ca-90210")
    body = r.data.decode()
    assert "Main St" in body
    assert "October 17, 1907" in body
    assert "O&#39;Rourke" in body
    # F-13: hours render as 12-hour times
    assert "9:00 am - 7:00 pm" in body
    assert "19:00" not in body
    # F-10: a 2-letter query means the state — Delaware offices only
    r = client.get("/locations/", query_string={
        "q": "DE", "service": "Self-Service Kiosk"})
    body = r.data.decode()
    assert "Bear" in body
    assert "Valdez" not in body          # no more fuzzy Alaska hits
    assert "location(s) shown" not in body  # count label removed (F-13)


def test_locations_state_search_shows_every_match(client):
    r = client.get("/locations/", query_string={"q": "DE"})
    body = r.data.decode()
    assert body.count('href="/locations/') >= 2 * 63   # 63 DE offices
    assert "Showing the first" not in body   # full listing, no cap note


def test_po_box_fees_and_reserve(client):
    r = client.get("/po-boxes/")
    body = r.data.decode()
    assert "$98.00" in body
    assert "Size 5" in body
    r = client.get("/locations/", query_string={"q": "02205"})
    key = re.search(r'href="/locations/([a-z0-9-]+)"', r.data.decode())
    assert key
    r = client.post(f"/po-boxes/reserve/{key.group(1)}",
                    data=with_csrf(client, f"/po-boxes/reserve/{key.group(1)}",
                                   {"size": "2", "period": "6 months"}))
    assert re.search(r"Box number:</strong> \d+", r.data.decode())


def test_store_cart_checkout(client):
    r = client.post("/store/cart/add", follow_redirects=True,
                    data=with_csrf(
                        client,
                        "/store/product/breast-cancer-research-stamps-S_555304",
                        {"sku": "555304", "qty": "2"}))
    assert r.status_code == 200
    r = client.get("/store/cart")
    assert "$40.00" in r.data.decode()
    r = client.post("/store/cart/add", follow_redirects=True,
                    data=with_csrf(
                        client,
                        "/store/product/christmas-cookies-stamps-S_686104",
                        {"sku": "686104", "qty": "1"}))
    r = client.get("/store/cart")
    assert "$56.40" in r.data.decode()
    # remove one line via the cart page's own form
    r = client.post("/store/cart/remove", follow_redirects=True,
                    data=with_csrf(client, "/store/cart", {"row": "1"}))
    assert r.status_code == 200
    r = client.post("/store/checkout", follow_redirects=True,
                    data=with_csrf(client, "/store/checkout",
                                   {"email": "me@example.com"}))
    body = r.data.decode()
    assert re.search(r"W[0-9A-F]{4,}", body)
    assert "Christmas Cookies" in body
    # cart is now empty
    r = client.get("/store/cart")
    assert "cart is empty" in r.data.decode().lower()


def test_store_second_checkout_gets_fresh_order_number(client):
    """F-11: two same-day checkouts from one session must not collide."""
    add = {"sku": "555304", "qty": "1"}
    client.post("/store/cart/add", follow_redirects=True,
                data=with_csrf(client,
                               "/store/product/breast-cancer-research-stamps-S_555304",
                               add))
    first = client.post("/store/checkout", follow_redirects=True,
                        data=with_csrf(client, "/store/checkout",
                                       {"email": "me@example.com"}))
    client.post("/store/cart/add", follow_redirects=True,
                data=with_csrf(client,
                               "/store/product/breast-cancer-research-stamps-S_555304",
                               add))
    second = client.post("/store/checkout", follow_redirects=True,
                        data=with_csrf(client, "/store/checkout",
                                       {"email": "me@example.com"}))
    n1 = re.search(r"W[0-9A-F]{7}", first.data.decode())
    n2 = re.search(r"W[0-9A-F]{7}", second.data.decode())
    assert n1 and n2 and n1.group(0) != n2.group(0)


def test_store_all_stamps_union(client):
    """F-9: All Stamps is a browsable union that includes the featured
    Breast Cancer Research sheet."""
    r = client.get("/store/stamps-all")
    body = r.data.decode()
    assert "Breast Cancer Research" in body
    assert "No products" not in body
    assert "Christmas Cookies" in body
    # the store home lists the category and a cart entry exists
    home = client.get("/store/").data.decode()
    assert 'href="/store/stamps-all"' in home


def test_hold_mail_flow_and_limits(carol):
    r = carol.get("/account")
    assert "HLD-748291" in r.data.decode()
    payload = {"start_date": "2026-10-01", "end_date": "2026-10-15",
               "option": "Hold all mail, deliver on end date"}
    r = carol.post("/manage/hold-mail/request",
                   data=with_csrf(carol, "/manage/hold-mail/request", payload))
    body = r.data.decode()
    m = re.search(r"(HLD-[A-Z0-9]+)", body)
    assert m
    # F-11: identical resubmission is idempotent
    r2 = carol.post("/manage/hold-mail/request",
                    data=with_csrf(carol, "/manage/hold-mail/request", payload))
    assert m.group(1) in r2.data.decode()
    # over the 30-day limit
    bad = {"start_date": "2026-10-01", "end_date": "2026-12-01",
           "option": "Hold all mail, deliver on end date"}
    r = carol.post("/manage/hold-mail/request",
                   data=with_csrf(carol, "/manage/hold-mail/request", bad))
    assert "at most 30 days" in r.data.decode()
    # in the past
    past = {"start_date": "2026-09-01", "end_date": "2026-09-15",
            "option": "Hold all mail, deliver on end date"}
    r = carol.post("/manage/hold-mail/request",
                   data=with_csrf(carol, "/manage/hold-mail/request", past))
    assert "cannot be in the past" in r.data.decode()


def test_change_of_address_flow(client):
    r = client.get("/manage/forward.htm")
    assert "identity validation" in r.data.decode().lower()
    assert "$1.25" in r.data.decode()      # F-4: upstream-verified fee
    assert "$1.05" not in r.data.decode()
    payload = {"move_type": "Family", "forward_type": "Regular",
               "start_date": "2026-10-05", "old_street": "88 State St",
               "old_city": "Boston", "old_state": "MA", "old_zip": "02110",
               "new_street": "12 Beacon St", "new_city": "Boston",
               "new_state": "MA", "new_zip": "02108",
               "email": "carol.d@test.com"}
    r = client.post("/manage/change-address/request",
                    data=with_csrf(client, "/manage/change-address/request",
                                   payload))
    body = r.data.decode()
    m = re.search(r"COA-[A-Z0-9]+", body)
    assert m
    assert "Family" in body
    assert "$1.25" in body
    # F-11: identical resubmission returns the same request
    r2 = client.post("/manage/change-address/request",
                     data=with_csrf(client, "/manage/change-address/request",
                                    payload))
    assert m.group(0) in r2.data.decode()
    assert r2.status_code == 200


def test_countries_index_and_detail(client):
    r = client.get("/international/countries")
    assert "Japan" in r.data.decode()
    r = client.get("/international/countries/japan")
    body = r.data.decode()
    assert "Prohibitions" in body
    assert "PS Form 2976-A" in body
    assert "Restrictions" in body
    r = client.get("/international/countries", query_string={"q": "German"})
    assert "Germany" in r.data.decode()


def test_claims_flow(bob):
    r = bob.get("/claims/file")
    assert "9405500000000000000004" in r.data.decode()
    payload = {"tracking": "9405500000000000000004", "kind": "damage",
               "article": "Vintage glass lamp",
               "note": "Shade arrived cracked.",
               "docs": ["Proof of insurance (Click-N-Ship receipt)",
                        "Photos of damaged packaging and item"]}
    r = bob.post("/claims/file",
                 data=with_csrf(bob, "/claims/file", payload))
    body = r.data.decode()
    claim = re.findall(r"CLM-[A-Z0-9]+", body)[0]
    assert "$280.00" in body
    r = bob.post("/claims/status", follow_redirects=True,
                 data=with_csrf(bob, "/claims/status",
                                {"claim_number": claim}))
    assert "Received" in r.data.decode()
    # F-11: identical resubmission is idempotent
    r2 = bob.post("/claims/file",
                  data=with_csrf(bob, "/claims/file", payload))
    assert claim in r2.data.decode()
    # seeded claim for Bob
    r = bob.get("/claims/CLM-55219088")
    assert "In Review" in r.data.decode()
    # unknown claim
    r = bob.post("/claims/status", follow_redirects=True,
                 data=with_csrf(bob, "/claims/status",
                                {"claim_number": "CLM-0000000"}))
    assert "No claim found" in r.data.decode()


def test_account_dashboard(bob):
    r = bob.get("/account")
    body = r.data.decode()
    assert "9405500000000000000003" in body
    assert "Informed Delivery" in body
    assert "PKG-338275" in body           # seeded pickup
    assert "W771882604" in body           # seeded order
    r = bob.get("/account/informed-delivery")
    assert "Lakeshore Hardware" in r.data.decode()


def test_saved_tracking(alice):
    r = alice.post("/account/saved/tracking", follow_redirects=True,
                   data=with_csrf(alice, "/tracking/9405500000000000000003",
                                  {"tracking": "9405500000000000000003",
                                   "label": "Books"}))
    assert r.status_code == 200
    r = alice.get("/account")
    assert "Books" in r.data.decode()


def test_newsroom(client):
    r = client.get("/newsroom/")
    body = r.data.decode()
    assert "National Releases" in body
    slug = re.search(r'href="(/newsroom/[^"]+)"', body).group(1)
    r = client.get(slug)
    assert r.status_code == 200
    r = client.get("/newsroom/service-alerts")
    assert "Service Alerts" in r.data.decode()


def test_newsroom_listing_deterministic(client):
    """Newest first; the two 2026-09-25 releases keep a fixed order."""
    body = client.get("/newsroom/").data.decode()
    titles = re.findall(r"<td><a href=\"/newsroom/[^\"]+\">([^<]+)</a>", body)
    assert titles[0] == "Squirrels &amp; Chipmunks in Snow Stamps Scurry Into Post Offices"
    assert titles[1] == "Introducing Linda McCartney Stamps"


def test_search(client):
    r = client.get("/search/", query_string={"q": "stamps"})
    body = r.data.decode()
    assert "Store Products" in body
    r = client.get("/search/", query_string={"q": "Beverly Hills"})
    assert "Post Offices" in r.data.decode()
    r = client.get("/search/", query_string={"q": "Japan"})
    assert "Countries" in r.data.decode()


def test_login_logout(client):
    r = client.post("/login", data=with_csrf(
        client, "/login", {"email": "alice.j@test.com", "password": "wrong"}))
    assert "Invalid email or password" in r.data.decode()
    client.post("/login", data=with_csrf(
        client, "/login", {"email": "alice.j@test.com",
                           "password": "TestPass123!"}))
    assert client.get("/account").status_code == 200
    client.get("/logout", follow_redirects=False)
    r = client.get("/account", follow_redirects=False)
    assert r.status_code == 302


def test_no_mojibake_on_content_surfaces(client):
    """F-5 regression: repaired text renders without UTF-8-as-latin-1
    mojibake on every content-bearing surface."""
    import sqlite3
    moji = re.compile(r'â|Â|[\x80-\x9f]')
    routes = ["/ship/mail-shipping-services.htm",
              "/ship/shipping-restrictions.htm", "/manage/forward.htm",
              "/manage/hold-mail.htm", "/help/claims.htm",
              "/international/priority-mail-international.htm",
              "/po-boxes/", "/newsroom/",
              "/search/?q=hold+mail", "/search/?q=stamps",
              "/store/product/christmas-cookies-stamps-S_686104"]
    import app as usps_app
    with usps_app.app.app_context():
        import sqlite3 as s3
        db = s3.connect(usps_app.app.config["SQLALCHEMY_DATABASE_URI"]
                        .replace("sqlite:///", ""), uri=False)
        for (slug,) in db.execute("SELECT slug FROM news_articles"):
            routes.append(f"/newsroom/{slug}")
    for route in routes:
        body = client.get(route).data.decode("utf-8", "replace")
        m = moji.search(body)
        assert not m, f"mojibake on {route}: {body[max(0, m.start()-30):m.start()+30]!r}"
