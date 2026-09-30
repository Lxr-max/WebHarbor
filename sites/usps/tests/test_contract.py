"""Contract tests: seeded data + every route family renders with markers."""
import json
import re

from app import (app, db, ContentPage, CountryInfo, ExtraService, NewsArticle,
                 PoBoxFee, PostOffice, Postmaster, Rate, ScanEvent, ServiceInfo,
                 Shipment, StoreProduct, User)


def test_health_payload(client):
    r = client.get("/_health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["site"] == "usps"
    assert data["pages"] >= 40
    assert data["rates"] >= 3000
    assert data["post_offices"] >= 4000
    assert data["countries"] >= 40
    assert data["products"] >= 40
    assert data["releases"] >= 12
    assert data["shipments"] >= 10
    assert data["users"] == 4


def test_benchmark_users_frozen():
    with app.app_context():
        users = {u.email: u for u in User.query.all()}
        assert set(users) == {"alice.j@test.com", "bob.c@test.com",
                              "carol.d@test.com", "dana.k@test.com"}
        for user in users.values():
            assert user.password_hash.startswith("$2b$12$")
            assert user.created_at == "2026-08-01"


def test_notice123_rates_seeded():
    with app.app_context():
        assert Rate.query.filter_by(table_code="pm").count() == 630
        assert Rate.query.filter_by(table_code="pme").count() == 639
        assert Rate.query.filter_by(table_code="ga").count() == 666
        assert Rate.query.filter_by(table_code="mm").count() == 70
        assert Rate.query.filter_by(table_code="pmi").count() == 1342
        assert Rate.query.filter_by(table_code="pmei").count() == 1384
        # First-Class Mail single piece
        stamped = {r.weight: r.price for r in
                   Rate.query.filter_by(table_code="fcm_letters_stamped")}
        assert stamped[1.0] == 0.82
        assert stamped[3.5] == 1.69
        postcard = Rate.query.filter_by(table_code="fcm_postcards").first()
        assert postcard.price == 0.65


def test_ground_advantage_ounce_rows_normalized():
    with app.app_context():
        weights = sorted({r.weight for r in
                          Rate.query.filter_by(table_code="ga")})
        assert 0.25 in weights          # '4 oz' row normalized to 0.25 lb
        assert 1.0 in weights            # '16 oz' row
        assert max(weights) == 70.0


def test_country_price_groups_real():
    with app.app_context():
        japan = CountryInfo.query.filter_by(name="Japan").first()
        assert japan.pmi_group == "17"
        assert japan.pmi_max_lbs == "66"
        prohibitions = json.loads(japan.prohibitions)
        assert any("Firearms" in p for p in prohibitions)
        services = json.loads(japan.services)
        assert services["pmi"]["weight_limit"] == "66 lbs"


def test_post_offices_from_postmaster_finder():
    with app.app_context():
        bh = PostOffice.query.filter_by(zip5="90210").first()
        assert bh is not None
        assert bh.name == "Beverly Hills"
        assert bh.state == "CA"
        assert bh.est_date == "1907-10-17"
        assert bh.postmaster == "Michael J. O'Rourke"
        assert PostOffice.query.count() >= 4000
        assert Postmaster.query.count() >= 100


def test_store_products_real():
    with app.app_context():
        bc = StoreProduct.query.filter_by(sku="555304").first()
        assert bc is not None
        assert bc.price == 20.00
        assert "Sheet of 20" in bc.name
        assert bc.image and bc.image.startswith("images/store/")
        cookies = StoreProduct.query.filter_by(sku="686104").first()
        assert cookies is not None and cookies.price == 16.40


def test_shipment_fixtures():
    with app.app_context():
        s = Shipment.query.filter_by(
            tracking_number="9405500000000000000001").first()
        assert s.status == "Delivered"
        assert s.insured_value == 350.00
        assert s.signature_required is True
        events = ScanEvent.query.filter_by(shipment_id=s.id).count()
        assert events == 7
        intl = Shipment.query.filter_by(
            tracking_number="9405500000000000000006").first()
        assert intl.is_international is True
        assert intl.dest_country == "Japan"


def test_extra_services_real_fees():
    with app.app_context():
        certified = ExtraService.query.filter_by(
            category="Certified Mail", label="Certified Mail").first()
        assert certified.price == 5.55
        rr = ExtraService.query.filter_by(
            category="Return Receipt").first()
        assert rr.price == 4.65


def test_po_box_fees():
    with app.app_context():
        fee = PoBoxFee.query.filter_by(schedule="market_dominant_6mo",
                                       size_label="2", fee_group="2").first()
        assert fee.fee == 98.00


def test_news_seeded():
    with app.app_context():
        releases = NewsArticle.query.filter_by(kind="release").all()
        assert len(releases) >= 12
        assert any("Holiday" in (r.title or "") or
                   "holiday" in (r.title or "") for r in releases)
        alerts = NewsArticle.query.filter_by(kind="alert").count()
        assert alerts >= 3


def test_content_pages_render(client):
    paths = ["ship/priority-mail.htm", "ship/ground-advantage.htm",
             "manage/hold-mail.htm", "manage/forward.htm",
             "international/customs-forms.htm", "help/claims.htm",
             "business/postage-options.htm", "shop/money-orders.htm"]
    for path in paths:
        r = client.get(f"/{path}")
        assert r.status_code == 200, path
        body = r.data.decode()
        assert "<h1>" in body
        assert "USPS" in body


def test_404(client):
    r = client.get("/ship/does-not-exist.htm")
    assert r.status_code == 404
    r = client.get("/nowhere/at-all")
    assert r.status_code == 404
