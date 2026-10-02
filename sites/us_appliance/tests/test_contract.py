"""Contract tests: every route family renders real upstream-sourced content."""
import json
import re


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    return resp.get_data(as_text=True)


def test_health(client):
    data = json.loads(_get(client, "/_health"))
    assert data["ok"] is True
    assert data["site"] == "us_appliance"
    assert data["products"] >= 12000
    assert data["categories"] >= 400
    assert data["brands"] >= 90
    assert data["reviews"] >= 200
    assert data["rebates"] >= 40
    assert data["guides"] == 9
    assert data["faq"] >= 10
    assert data["users"] == 4
    assert data["orders"] >= 8


def test_homepage(client):
    html = _get(client, "/")
    for marker in ["Shop by Appliance Category", "Deals Today",
                   "Order With Confidence", "Shop Top Brands",
                   "QuickShip Items", "Huge Fall Savings"]:
        assert marker in html, f"homepage missing {marker!r}"
    assert "/static/images/home/tile_" in html
    assert "/static/images/products/" in html


def test_category_landing_and_grid(client):
    html = _get(client, "/ranges.html")
    assert "Shop by Range Fuel Type" in html
    assert "Electric Ranges" in html and "Gas Ranges" in html
    assert "products" in html
    assert "/static/images/category_tiles/" in html
    # filters + sort present
    assert 'name="price_from"' in html and 'name="brand"' in html
    assert "Price: Ascending" in html


def test_category_filters(client):
    base = _get(client, "/gas-ranges.html?query=c407")
    # on-sale filter
    html = _get(client, "/gas-ranges.html?query=c407&on_sale=1")
    assert "products" in html
    # price range filter
    html = _get(client, "/gas-ranges.html?query=c407&price_from=500&price_to=1000")
    assert "products" in html
    assert html != base


def test_search_products_and_content_tabs(client):
    html = _get(client, "/search.php?search_query=ranges&section=product")
    assert "Products (" in html
    assert "News &amp; Information (" in html
    assert "Advanced Search" in html
    assert "card-title" in html
    content = _get(client, "/search.php?search_query=ranges&section=content")
    assert "Buying Guide" in content


def test_search_brand_filter_and_sort(client):
    html = _get(client, "/search.php?mode=1&search_query_adv=dishwasher&brand=Bosch")
    assert "Bosch" in html
    cards = re.findall(r'data-test="card-(\d+)"', html)
    assert len(cards) == 12
    html2 = _get(client,
                 "/search.php?search_query=dishwasher&sort=priceasc&section=product")
    prices = [float(v.replace(",", "").replace("$", ""))
              for v in re.findall(r'class="price price--now">(\$[\d,.]+)<', html2)]
    assert prices == sorted(prices)


def test_product_page_real_facts(client):
    html = _get(client, "/jgbs66rekss.html")
    assert "GE JGBS66REKSS" in html
    assert "jgbs66rekss" in html            # model
    assert "18571" in html                  # code
    assert "$823.00" in html                # captured price
    assert "Sale ends Sept 30" in html       # captured promo message
    assert "Steam clean" in html            # captured feature bullet
    assert "Product Specifications" in html  # spec sheet PDF link
    assert "Check Availability" in html
    assert "Frequently Bought Together" in html
    assert "15 Months Special Finance Offer" in html


def test_product_gallery_and_color_variants(client):
    html = _get(client, "/jgbs66rekss.html")
    assert "productView-thumbnail" in html
    assert "jgbs66dekww" in html            # captured color variant links


def test_discontinued_product(client):
    html = _get(client, "/mgd8630hw.html")
    assert "THIS ITEM IS DISCONTINUED" in html
    assert 'id="form-action-addToCart"' not in html
    assert 'data-code=' not in html


def test_sale_product_with_was_price(client):
    html = _get(client, "/hbc163ess.html")
    assert "$2,095.00" in html              # captured Now price
    assert "$3,299.00" in html              # captured Was price
    assert 'You save <span data-product-price-saved>$1,204.00' in html


def test_brand_pages(client):
    html = _get(client, "/shopbybrand.html")
    assert "Shop By Brand" in html
    assert "General Electric" in html and "Rebate Offers" in html
    html = _get(client, "/brand/general-electric")
    assert "General Electric Appliances" in html
    assert "products" in html


def test_cart_flow(client):
    client.post("/cart.php?action=add",
                data={"product_id": 21476, "qty": 1})
    html = _get(client, "/cart.php")
    assert "JGBS66REKSS" in html
    assert "$823.00" in html
    assert "$99" in html                    # under-threshold shipping


def test_cart_shipping_threshold(client):
    client.post("/cart.php?action=add", data={"product_id": 25555, "qty": 1})
    html = _get(client, "/cart.php")
    assert "FREE standard delivery" in html


def test_deals_and_rebates_pages(client):
    html = _get(client, "/hugepricecuts.html")
    assert "Appliance Deals Today" in html
    assert "Huge Fall Sale!" in html
    html = _get(client, "/rebates.html")
    assert "Appliance Rebates" in html
    assert "Save $300 when you buy an Asko Washer and Dryer" in html
    assert "Expires Dec 31" in html


def test_delivery_page_real_rules(client):
    html = _get(client, "/freedelivery.html")
    assert "Nationwide Delivery" in html
    assert "$999" in html
    assert "In-Home Delivery" in html
    assert "$199" in html
    assert "1–3 weeks" in html
    assert "$5.99" in html


def test_finance_offers(client):
    html = _get(client, "/financeoffers.html")
    assert "0% Interest If Paid In Full In 15 Months" in html
    assert "0% Interest If Paid In Full In 6 Months Storewide" in html
    assert "$200 or more" in html
    assert "Bosch" in html and "Whirlpool" in html


def test_testimonials_real_reviews(client):
    html = _get(client, "/testimonials.html")
    assert "US Appliance Customer Reviews" in html
    assert "20,841" in html
    assert "97%" in html
    assert "Verified Customer" in html
    assert "4- or 5-stars" in html


def test_faq_real_content(client):
    html = _get(client, "/faq.html")
    assert "Frequently Asked Questions" in html
    assert "Is shipping really FREE?" in html
    assert "110% of the difference" in html
    assert "48 hours" in html


def test_order_tracking_page(client):
    html = _get(client, "/ordertracking.html")
    assert "R+L Carriers" in html
    assert "Maersk" in html
    assert "FedEx" in html
    assert "1-800-543-5589" in html


def test_guides(client):
    html = _get(client, "/buyingguide.html")
    assert "Refrigerator Buying Guide" in html
    html = _get(client, "/guides/refrigerator.html")
    assert "Refrigerator Buying Guide" in html
    assert len(html) > 4000


def test_support_pages(client):
    for path, marker in [
        ("/cusser.html", "Customer Service"),
        ("/contactus2.html", "Auburn Hills, MI 48326"),
        ("/returninformation.html", "Returns"),
        ("/whyusappliance.html", "Why Shop US Appliance"),
        ("/warrantyoptions.html", "US Appliance Service Plans"),
        ("/clearance.html", "Deals"),
        ("/price-match-request.html", "110% of the difference"),
        ("/in-stock-message-2.html", "Stock Item"),
    ]:
        html = _get(client, path)
        assert marker in html, f"{path} missing {marker!r}"


def test_availability_check(client):
    resp = client.post("/availability",
                       data={"product_id": 21476, "zip": "48083"})
    data = json.loads(resp.get_data(as_text=True))
    assert data["ok"] is True
    assert "available for delivery" in data["message"]
    resp = client.post("/availability",
                       data={"product_id": 21476, "zip": "96"})
    data = json.loads(resp.get_data(as_text=True))
    assert data["ok"] is False


def test_images_served(client):
    resp = client.get("/static/images/products/21476_card.jpg")
    assert resp.status_code == 200
    data = resp.get_data()
    assert data[:2] == b"\xff\xd8"
    assert len(data) > 4000


def test_404(client):
    resp = client.get("/definitely-not-a-page.html")
    assert resp.status_code == 404
    assert b"Page Not Found" in resp.get_data()
