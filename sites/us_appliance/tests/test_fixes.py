"""CSRF + page-title + count-consistency contract tests.

Covers the three functional fixes from the us_appliance review round:
- CSRF: every state-changing POST form carries a flask-wtf token and a
  tokenless POST is rejected; the read-only /availability JSON endpoint
  stays reachable for the product-page AJAX check.
- <title>: support/category/guide pages use their verbatim upstream
  per-page titles instead of the site-wide default.
- Brand pages: the blurb count and the result-bar count use the same
  (available-products) caliber.
"""
import html as html_mod
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def _title(page_html):
    return html_mod.unescape(
        re.search(r"<title>(.*?)</title>", page_html, re.S).group(1)).strip()


def _token_from(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert m, "no csrf_token input rendered"
    return m.group(1)


# --------------------------------------------------------------------- CSRF
def test_forms_render_csrf_token(client):
    # seed one cart row so the cart update/remove form renders
    client.post("/cart.php?action=add", data={"product_id": 21476, "qty": 1})
    for path, form_marker in [
        ("/", "usa-newsletter-form"),                       # footer newsletter
        ("/jgbs66rekss.html", "form-action"),               # product add-to-cart
        ("/gas-ranges.html", "card-add"),                   # grid card add-to-cart
        ("/cart.php", "cart-form"),                          # cart update/remove
        ("/checkout", "checkout-form"),                      # checkout
        ("/login.php", "login-form"),                         # sign in
        ("/login.php?action=create_account", "login-form"),  # register
        ("/ordertracking.html", "lookup-form"),              # order tracking
        ("/price-match-request.html", "pricematch-form"),   # price match
    ]:
        page_html = _get(client, path)
        assert form_marker in page_html, f"{path} missing {form_marker!r}"
        assert 'name="csrf_token"' in page_html, f"{path} form lacks csrf_token"


def test_csrf_rejects_tokenless_post(csrf_client):
    resp = csrf_client.post("/newsletter",
                            data={"nl_email": "no-token@example.com"})
    assert resp.status_code == 400, "tokenless POST must be rejected"
    resp = csrf_client.post("/cart.php?action=add",
                            data={"product_id": 21476, "qty": 1})
    assert resp.status_code == 400
    resp = csrf_client.post("/price-match-request.html",
                            data={"name": "X", "email": "x@example.com",
                                  "product": "p", "competitor": "c",
                                  "price": "10"})
    assert resp.status_code == 400


def test_csrf_accepts_valid_token(csrf_client):
    # newsletter: fetch home page, extract token, post with it
    token = _token_from(_get(csrf_client, "/"))
    resp = csrf_client.post("/newsletter",
                            data={"nl_email": "token-ok@example.com",
                                  "csrf_token": token},
                            follow_redirects=True)
    assert resp.status_code == 200
    assert b"signed up for deals and offers" in resp.get_data()


def test_availability_endpoint_is_csrf_exempt(csrf_client):
    # product-page AJAX availability check posts via fetch() without a form
    resp = csrf_client.post("/availability",
                            data={"product_id": 21476, "zip": "48083"})
    assert resp.status_code == 200
    assert b"available for delivery" in resp.get_data()


# ------------------------------------------------------------------- titles
def test_support_page_titles_upstream(client):
    for path, want in [
        ("/freedelivery.html", "Delivery"),
        ("/financecenter.html", "Appliance Finance Options - US Appliance"),
        ("/financeoffers.html", "Appliance Finance Offers"),
        ("/rebates.html", "Appliance Rebates | Save Money on Appliances"),
        ("/hugepricecuts.html", "Home Appliances On Sale. Huge Discounts"),
        ("/clearance.html", "Appliances On Sale Today US Appliance"),
        ("/testimonials.html", "US Appliance Customer Reviews"),
        ("/faq.html", "Frequently Asked Questions"),
        ("/buyingguide.html", "Appliance Buying Guides"),
        ("/guides/range.html", "Kitchen Range Buying Guide"),
        ("/guides/refrigerator.html", "Kitchen Refrigerator Buying Guide"),
        ("/contactus2.html", "Contact US Appliance - Phone, Chat or Email"),
        ("/ordertracking.html", "Order Tracking"),
        ("/cusser.html", "Customer Service"),
        ("/returninformation.html", "Returns"),
        ("/whyusappliance.html",
         "Shop US Appliance for the Lowest Online Prices"),
        ("/shopbybrand.html", "Shop By Brand - US Appliance"),
        ("/price-match-request.html", "Price Match Request"),
        ("/search.php?search_query=ranges", "US Appliance"),
    ]:
        assert _title(_get(client, path)) == want, path


def test_category_page_titles_upstream(client):
    for path, want in [
        ("/gas-ranges.html",
         'Gas Ranges for Sale | 30", 36" & Pro-Style | Top Brands | '
         'US Appliance'),
        ("/dishwasher.html",
         "Best Dishwashers 2026: Buy Dishwashers Online at Best Prices"),
        ("/frdore.html",
         "Best French Door Refrigerators 2026: Shop 3-Door, 4-Door & "
         "Counter-Depth | US-Appliance"),
        ("/cooking.html",
         "Big Selection of Ranges, Cooktops, Ovens and more"),
        ("/sidebyside.html",
         "Side by Side Refrigerators | Side by Side Fridge | Refrigerators"),
        ("/front-load.html", "Front Loads - US Appliance"),
        ("/top-load.html", "Top Loads - US Appliance"),
    ]:
        assert _title(_get(client, path)) == want, path


def test_home_and_product_titles_unchanged(client):
    assert _title(_get(client, "/")) == \
        "US Appliance Low Prices Online on Major Home Appliances."
    assert _title(_get(client, "/jgbs66rekss.html")).startswith(
        'GE JGBS66REKSS 30" Free-Standing')


# ------------------------------------------------- brand page count caliber
def test_brand_page_counts_consistent(client):
    for slug in ("cafe", "viking", "samsung", "general-electric"):
        html = _get(client, f"/brand/{slug}")
        blurb = re.search(
            r'<p class="category-blurb">(\d+) ([A-Za-z&;\s]+?) products available',
            html)
        result = re.search(
            r'<p class="result-count">(\d+) products</p>', html)
        assert blurb, f"/brand/{slug}: blurb count not found"
        assert result, f"/brand/{slug}: result count not found"
        assert blurb.group(1) == result.group(1), (
            f"/brand/{slug}: blurb says {blurb.group(1)} available but the "
            f"grid shows {result.group(1)}")


def test_deals_category_links_use_hash_filter_urls(client):
    # The deals page keeps the upstream hash-fragment URLs verbatim;
    # static/js/site.js translates the on-sale hash to ?on_sale=1.
    html = _get(client, "/hugepricecuts.html")
    assert re.search(
        r'href="/frdore\.html#query=c232&amp;filter_on-sale\.filter=on%20sale%20today"',
        html), "upstream on-sale hash link missing"
    assert re.search(
        r'href="/dishwasher\.html#query=c172&amp;filter_on-sale\.filter=on%20sale%20today"',
        html), "upstream on-sale hash link missing"
